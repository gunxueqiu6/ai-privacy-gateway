path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add imports
old_import = "from jose import JWTError, jwt"
new_import = """from jose import JWTError, jwt
import uuid as _uuid

from payment import get_paypal_client, PayPalError
from license import get_license_service, LicenseError"""
content = content.replace(old_import, new_import)

# Add payment + license endpoints before the health endpoint
health_endpoint = '@app.get("/health")'
new_endpoints = '''
# ==================== Payment API ====================

@app.post("/api/payment/create-order")
@limiter.limit("10/minute")
async def payment_create_order(request: Request) -> JSONResponse:
    """Create a PayPal order for a Pro or Enterprise license."""
    paypal = get_paypal_client()
    if not paypal:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    body = await request.json()
    tier = body.get("tier", "pro")
    email = body.get("email", "")

    if tier not in ("pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid tier. Must be 'pro' or 'enterprise'")

    try:
        order = await paypal.create_order(amount=0, tier=tier, email=email)
        return JSONResponse({
            "id": order["id"],
            "status": order["status"],
            "tier": tier,
        })
    except PayPalError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))


@app.post("/api/payment/capture-order")
@limiter.limit("10/minute")
async def payment_capture_order(request: Request) -> JSONResponse:
    """Capture a PayPal payment and issue a license."""
    paypal = get_paypal_client()
    if not paypal:
        raise HTTPException(status_code=503, detail="Payment service not configured")

    body = await request.json()
    order_id = body.get("order_id", "")
    email = body.get("email", "")
    tier = body.get("tier", "pro")

    if not order_id:
        raise HTTPException(status_code=400, detail="order_id is required")

    if tier not in ("pro", "enterprise"):
        raise HTTPException(status_code=400, detail="Invalid tier")

    try:
        # Capture payment
        capture = await paypal.capture_order(order_id)

        if capture.get("status") != "COMPLETED":
            return JSONResponse(
                status_code=402,
                content={"status": "failed", "message": "Payment not completed"}
            )

        # Generate license
        license_svc = get_license_service()
        team_id = f"T{int(_uuid.uuid4().hex[:8], 16) % 10**8:08d}"
        license_token = license_svc.sign_license(
            team_id=team_id,
            tier=tier,
            email=email,
        )

        # Decode to get expiration
        from datetime import datetime, timezone
        payload = license_svc.verify_license(license_token)[1]
        expires_at = datetime.fromtimestamp(
            payload["exp"], tz=timezone.utc
        ).strftime("%Y-%m-%d") if payload else "Unknown"

        # Save to database
        license_id = str(_uuid.uuid4())
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        db.save_license(
            license_id=license_id,
            team_id=team_id,
            tier=tier,
            seats=payload["seats"] if payload else 20,
            email=email,
            issued_at=now,
            expires_at=expires_at,
            jwt_token=license_token,
            payment_id=order_id,
        )

        db.log_audit(None, "license_issued", {
            "team_id": team_id,
            "tier": tier,
            "email": email,
            "payment_id": order_id,
        })

        tier_name = "Pro (Team)" if tier == "pro" else "Enterprise"
        return JSONResponse({
            "status": "completed",
            "license_key": license_token,
            "team_id": team_id,
            "tier": tier,
            "tier_name": tier_name,
            "expires_at": expires_at,
        })

    except PayPalError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e))
    except LicenseError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/payment/webhook")
@limiter.limit("30/minute")
async def payment_webhook(request: Request) -> JSONResponse:
    """Handle PayPal webhook events."""
    paypal = get_paypal_client()
    if not paypal:
        return JSONResponse(status_code=200, content={"status": "ignored"})

    body = await request.json()
    headers = dict(request.headers)

    verified, event_data = await paypal.handle_webhook(body, headers)

    if verified:
        logger.info(f"Verified PayPal webhook: {event_data}")
        db.log_audit(None, "payment_webhook", event_data or {})

    return JSONResponse({"status": "received"})


# ==================== License Management API ====================

@app.get("/admin/license")
@limiter.limit("10/minute")
async def admin_license_status(request: Request) -> JSONResponse:
    """View current license status (requires admin auth)."""
    await require_admin(request)

    from datetime import datetime, timezone

    license_svc = get_license_service()
    current_token = config.LICENSE_KEY

    if not current_token:
        return JSONResponse({
            "tier": config.tier,
            "status": "lite",
            "seats": 1,
            "message": "No license activated. Running in Lite mode.",
        })

    valid, payload, error = license_svc.verify_license(current_token)
    revoked = db.is_token_revoked(payload["tid"] if payload else "")

    now_ts = int(datetime.now(timezone.utc).timestamp())
    expires_ts = payload.get("exp", 0) if payload else 0
    days_left = max(0, (expires_ts - now_ts) // 86400)

    return JSONResponse({
        "tier": config.tier,
        "status": "active" if valid and not revoked else "invalid",
        "seats": config.license_seats,
        "team_id": config.license_team_id,
        "expires_at": datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat() if expires_ts else None,
        "days_left": days_left,
        "revoked": revoked,
        "error": error if not valid else None,
    })


@app.post("/admin/license/activate")
@limiter.limit("5/minute")
async def admin_license_activate(request: Request) -> JSONResponse:
    """Activate a license key (requires admin auth)."""
    await require_admin(request)

    body = await request.json()
    license_key = body.get("license_key", "").strip()

    if not license_key:
        raise HTTPException(status_code=400, detail="license_key is required")

    license_svc = get_license_service()

    # Verify the license
    valid, payload, error = license_svc.verify_license(license_key)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Invalid license: {error}")

    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid license payload")

    team_id = payload.get("tid", "")
    tier = payload.get("tier", "")
    seats = payload.get("seats", 1)

    # Check if this team's license is revoked
    if db.is_token_revoked(team_id):
        raise HTTPException(status_code=403, detail="This license has been revoked")

    # Save to file
    license_file = config.LICENSE_FILE
    with open(license_file, "w", encoding="utf-8") as f:
        f.write(license_key)

    # Update runtime config
    config.tier = tier
    config.license_seats = seats
    config.license_team_id = team_id
    config.LICENSE_KEY = license_key

    from datetime import datetime, timezone
    expires_ts = payload.get("exp", 0)
    config.license_expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat()

    db.log_audit(None, "license_activated", {
        "team_id": team_id,
        "tier": tier,
        "seats": seats,
    })

    logger.info(f"License activated: tier={tier}, team={team_id}, seats={seats}")

    return JSONResponse({
        "status": "ok",
        "message": "License activated successfully",
        "tier": tier,
        "team_id": team_id,
        "seats": seats,
    })


@app.post("/admin/license/refresh")
@limiter.limit("5/minute")
async def admin_license_refresh(request: Request) -> JSONResponse:
    """Refresh the current license status (re-read from file)."""
    await require_admin(request)

    # Reload from file if exists
    import os as _os
    license_file = config.LICENSE_FILE
    if not _os.path.exists(license_file):
        # Reset to lite
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "No license file found. Running in Lite mode.",
        })

    with open(license_file, "r", encoding="utf-8") as f:
        license_key = f.read().strip()

    if not license_key:
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "Empty license file. Running in Lite mode.",
        })

    license_svc = get_license_service()
    valid, payload, error = license_svc.verify_license(license_key)

    if not valid:
        logger.warning(f"License refresh failed: {error}")
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": f"License invalid: {error}. Downgraded to Lite.",
        })

    if payload is None:
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "License payload is empty. Running in Lite mode.",
        })

    team_id = payload.get("tid", "")
    if db.is_token_revoked(team_id):
        config.tier = "lite"
        config.license_seats = 1
        config.license_team_id = None
        config.license_expires_at = None
        config.LICENSE_KEY = ""
        return JSONResponse({
            "status": "ok",
            "tier": "lite",
            "message": "License has been revoked. Downgraded to Lite.",
        })

    config.tier = payload.get("tier", "lite")
    config.license_seats = payload.get("seats", 1)
    config.license_team_id = team_id
    config.LICENSE_KEY = license_key

    from datetime import datetime, timezone
    expires_ts = payload.get("exp", 0)
    config.license_expires_at = datetime.fromtimestamp(expires_ts, tz=timezone.utc).isoformat()

    return JSONResponse({
        "status": "ok",
        "tier": config.tier,
        "team_id": config.license_team_id,
        "seats": config.license_seats,
        "expires_at": config.license_expires_at,
    })


@app.get("/admin/license/check")
@limiter.limit("30/minute")
async def admin_license_check() -> JSONResponse:
    """Public endpoint to check license status (no auth required)."""
    return JSONResponse({
        "tier": config.tier,
        "team_id": config.license_team_id,
        "seats": config.license_seats,
        "expires_at": config.license_expires_at,
    })

'''

content = content.replace(health_endpoint, new_endpoints + health_endpoint)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("main.py updated successfully")
