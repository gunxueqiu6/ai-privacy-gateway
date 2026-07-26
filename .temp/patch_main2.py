path = r"G:\projects\ai数据隐私隔离\main.py"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# Add paypal-config endpoint after the payment_create_order endpoint
marker = "@app.post(\"/api/payment/capture-order\")"
new_endpoint = '''@app.get("/api/payment/paypal-config")
@limiter.limit("30/minute")
async def payment_paypal_config(request: Request) -> JSONResponse:
    """Return PayPal client configuration for the frontend."""
    client_id = os.environ.get("PAYPAL_CLIENT_ID", "")
    if not client_id:
        return JSONResponse({
            "client_id": "",
            "mode": config.PAYPAL_MODE,
            "configured": False,
        })
    return JSONResponse({
        "client_id": client_id,
        "mode": config.PAYPAL_MODE,
        "configured": True,
    })


'''
content = content.replace(marker, new_endpoint + marker)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Added paypal-config endpoint to main.py")
