path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add imports for new modules
old_import = "from team import ("
new_import = "from reports import (get_daily_report, get_weekly_report, get_monthly_report, export_report_csv, get_summary_stats)\nfrom alerts import get_alert_engine\nfrom redis_cache import get_redis_cache\nfrom team import ("
content = content.replace(old_import, new_import)

# Add report and alert endpoints before the startup block
marker = "# ==================== Team Management API ===================="
new_endpoints = """# ==================== Statistics Reports API ====================

@app.get("/admin/reports/daily")
@limiter.limit("10/minute")
async def admin_reports_daily(request: Request, date: Optional[str] = None) -> JSONResponse:
    \"\"\"Get daily statistics report.\"\"\"
    await require_admin(request)
    await require_tier("pro")
    team_id = config.license_team_id
    report = get_daily_report(team_id, date)
    return JSONResponse(report)


@app.get("/admin/reports/weekly")
@limiter.limit("10/minute")
async def admin_reports_weekly(request: Request, end_date: Optional[str] = None) -> JSONResponse:
    \"\"\"Get weekly statistics report (daily breakdown for 7 days).\"\"\"
    await require_admin(request)
    await require_tier("pro")
    team_id = config.license_team_id
    report = get_weekly_report(team_id, end_date)
    return JSONResponse({"days": report, "count": len(report)})


@app.get("/admin/reports/monthly")
@limiter.limit("10/minute")
async def admin_reports_monthly(request: Request, year: Optional[int] = None, month: Optional[int] = None) -> JSONResponse:
    \"\"\"Get monthly statistics report.\"\"\"
    await require_admin(request)
    await require_tier("pro")
    team_id = config.license_team_id
    report = get_monthly_report(team_id, year, month)
    return JSONResponse({"days": report, "count": len(report)})


@app.get("/admin/reports/summary")
@limiter.limit("10/minute")
async def admin_reports_summary(request: Request, days: int = 30) -> JSONResponse:
    \"\"\"Get aggregated summary stats for the last N days.\"\"\"
    await require_admin(request)
    await require_tier("pro")
    team_id = config.license_team_id
    stats = get_summary_stats(team_id, days)
    return JSONResponse(stats)


@app.get("/admin/reports/export")
@limiter.limit("5/minute")
async def admin_reports_export(
    request: Request,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> Response:
    \"\"\"Export stats as CSV.\"\"\"
    await require_admin(request)
    await require_tier("pro")
    team_id = config.license_team_id
    csv_data = export_report_csv(team_id, start_date, end_date)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=privacy_gateway_report.csv"},
    )


# ==================== Alert Engine API ====================

@app.get("/admin/alerts/status")
@limiter.limit("10/minute")
async def admin_alerts_status(request: Request) -> JSONResponse:
    \"\"\"Get alert engine status.\"\"\"
    await require_admin(request)
    await require_tier("enterprise")
    engine = get_alert_engine()
    return JSONResponse({
        "rules_count": len(engine.rules),
        "rules": [{"name": r.name, "condition": r.condition, "actions": r.actions} for r in engine.rules],
    })


@app.post("/admin/alerts/test")
@limiter.limit("5/minute")
async def admin_alerts_test(request: Request) -> JSONResponse:
    \"\"\"Test alert notifications by triggering a sample alert.\"\"\"
    await require_admin(request)
    await require_tier("enterprise")
    engine = get_alert_engine()
    context = {
        "stats": {"5min": 15000},
        "license": {"expires_in": 3},
    }
    triggered = await engine.process(context)
    return JSONResponse({
        "triggered": len(triggered),
        "alerts": triggered,
    })


# ==================== Cache Status API ====================

@app.get("/admin/cache/status")
@limiter.limit("10/minute")
async def admin_cache_status(request: Request) -> JSONResponse:
    \"\"\"Get cache (Redis) status.\"\"\"
    await require_admin(request)
    cache = get_redis_cache()
    healthy = await cache.health_check() if cache.available else False
    return JSONResponse({
        "available": cache.available,
        "healthy": healthy,
        "type": "redis" if cache.available else "none",
    })


# ==================== Team Management API ===================="""

content = content.replace(marker, new_endpoints)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("main.py updated with Phase 4 endpoints")
