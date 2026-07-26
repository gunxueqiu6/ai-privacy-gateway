path = r"G:\projects\ai数据隐私隔离\website-astro\src\pages\pricing.astro"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Change API_BASE from trycloudflare to same-origin
old_api = "window.__PAYMENT_API_BASE__ = import.meta.env.PUBLIC_API_BASE || 'https://surf-illinois-servers-wrote.trycloudflare.com';"
new_api = "window.__PAYMENT_API_BASE__ = import.meta.env.PUBLIC_API_BASE || '';"
content = content.replace(old_api, new_api)

# 2. Update create-order to match our API (add email to request, handle new response format)
old_create = """createOrder: async () => {
          const resp = await fetch(`${API_BASE}/api/payment/create-order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tier: currentTier })
          });"""
new_create = """createOrder: async () => {
          const resp = await fetch(`${API_BASE}/api/payment/create-order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tier: currentTier, email: currentEmail })
          });"""
content = content.replace(old_create, new_create)

# 3. Update onApprove/capture to use /api/payment/capture-order instead of /api/payment/complete
old_capture = """const resp = await fetch(`${API_BASE}/api/payment/complete`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                order_id: data.orderID,
                customer_email: currentEmail,
                tier: currentTier
              })
            });"""
new_capture = """const resp = await fetch(`${API_BASE}/api/payment/capture-order`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                order_id: data.orderID,
                email: currentEmail,
                tier: currentTier
              })
            });"""
content = content.replace(old_capture, new_capture)

# 4. Update result display to use new response field names
old_result = """if (result.status === 'completed') {
              showResult('支付成功!',
                `<div class="license-box">
                  <p>您的 License Key:</p>
                  <code class="license-key">${result.license_key}</code>
                  <p class="license-info">版本: ${result.tier === 'pro' ? 'Pro 团队版' : 'Enterprise 企业版'}</p>
                  <p class="license-info">有效期至: ${result.expires_at}</p>
                  <p class="license-info">License 已发送至 ${currentEmail}</p>
                </div>`
              );"""
new_result = """if (result.status === 'completed') {
              showResult('支付成功!',
                `<div class="license-box">
                  <p>您的 License Key:</p>
                  <code class="license-key">${result.license_key}</code>
                  <p class="license-info">版本: ${result.tier_name}</p>
                  <p class="license-info">团队 ID: ${result.team_id}</p>
                  <p class="license-info">有效期至: ${result.expires_at}</p>
                  <p class="license-info">License 已发送至 ${currentEmail}</p>
                </div>`
              );"""
content = content.replace(old_result, new_result)

# 5. Update paypal-config endpoint to use same-origin
old_config = """const resp = await fetch(`${API_BASE}/api/paypal-config`);"""
new_config = """const resp = await fetch(`${API_BASE}/api/payment/paypal-config`);"""
content = content.replace(old_config, new_config)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Updated pricing.astro")
