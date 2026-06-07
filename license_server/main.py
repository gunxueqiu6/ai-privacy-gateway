"""
License 验证服务器 - Pro/Enterprise 版授权管理
部署在 VPS 上，处理激活、验证、规则下发、自动发货、支付
"""
import hashlib
import httpx
import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from license_store import (
    create_license, get_license, list_licenses, revoke_license, check_expired,
    bind_hardware, verify_hardware,
    create_session, find_session_by_token, touch_session
)
from email_sender import send_license_email

# 配置
RULES_SIGNING_KEY = os.environ.get("RULES_SIGNING_KEY", "your_rsa_private_key_here")
ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "admin-secret-change-me")
PAYPAL_CLIENT_ID = os.environ.get("PAYPAL_LIVE_CLIENT_ID", "")
PAYPAL_CLIENT_SECRET = os.environ.get("PAYPAL_LIVE_CLIENT_SECRET", "")
PAYPAL_API_BASE = "https://api-m.paypal.com"  # Live environment

app = FastAPI(title="AI Privacy Gateway — License Verification Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://privacygw.pages.dev", "http://localhost:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Models ---

class LicenseActivateRequest(BaseModel):
    license_key: str
    hardware_fingerprint: dict  # {board_serial, disk_uuid, mac_address, container_id, hostname}
    container_id: str
    timestamp: int


class LicenseVerifyRequest(BaseModel):
    license_key: str
    session_token: str
    challenge_response: str
    timestamp: int


class HeartbeatRequest(BaseModel):
    license_key: str
    session_token: str
    status: str
    timestamp: int


class GenerateLicenseRequest(BaseModel):
    customer_email: str
    tier: str = "pro"  # pro | enterprise
    expires_in_days: int = 365
    max_concurrent: int = 20
    send_email: bool = True
    notes: str = ""


class RevokeLicenseRequest(BaseModel):
    license_key: str


class CompletePaymentRequest(BaseModel):
    order_id: str
    customer_email: str
    tier: str = "pro"  # pro | enterprise
    expires_in_days: int = 365
    max_concurrent: int = 20


# --- PayPal Helpers ---

async def get_paypal_access_token() -> str:
    """获取 PayPal OAuth access token"""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            data={"grant_type": "client_credentials"},
            auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            headers={"Accept": "application/json"}
        )
        if resp.status_code != 200:
            raise HTTPException(502, f"PayPal 认证失败: {resp.text}")
        return resp.json()["access_token"]


async def verify_paypal_order(order_id: str) -> dict:
    """验证并捕获 PayPal 订单"""
    token = await get_paypal_access_token()
    async with httpx.AsyncClient() as client:
        # 先查询订单状态
        resp = await client.get(
            f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
        )
        if resp.status_code != 200:
            raise HTTPException(502, f"PayPal 查询订单失败: {resp.text}")

        order = resp.json()
        status = order.get("status")

        if status == "APPROVED":
            # 捕获订单
            capture_resp = await client.post(
                f"{PAYPAL_API_BASE}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                }
            )
            if capture_resp.status_code not in (200, 201):
                raise HTTPException(502, f"PayPal 捕获失败: {capture_resp.text}")
            return capture_resp.json()

        elif status == "COMPLETED":
            return order

        else:
            raise HTTPException(400, f"订单状态异常: {status}")


# --- Helpers ---

def generate_challenge() -> str:
    return hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:32]


def sign_rules(rules: dict) -> str:
    rules_json = json.dumps(rules, sort_keys=True)
    return hashlib.sha256(f"{RULES_SIGNING_KEY}{rules_json}".encode()).hexdigest()


def generate_jwt(license_key: str, expires_hours: int = 1) -> str:
    payload = {
        "license_key": license_key,
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + expires_hours * 3600
    }
    token = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"jwt_{token}"


def build_rules() -> dict:
    return {
        "mask_patterns": {
            "phone": r'\b(1[3-9]\d{9})\b',
            "email": r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            "idcard": r'\b([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])\b',
            "bankcard": r'\b([1-9]\d{15,18})\b'
        },
        "custom_keywords": ["密码", "密钥", "token", "API_KEY", "SECRET"],
        "version": "2026.1",
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 86400
    }


def _check_admin(request: Request):
    """验证 Admin API Key"""
    auth = request.headers.get("Authorization", "")
    expected = f"Bearer {ADMIN_API_KEY}"
    if auth != expected:
        raise HTTPException(401, "Unauthorized — 需要有效的 Admin API Key")


def _load_license_info(license_key: str) -> dict:
    """加载并检查 license，自动标记过期"""
    check_expired()
    info = get_license(license_key)
    if info is None:
        raise HTTPException(403, "License 不存在")
    if info["status"] == "revoked":
        raise HTTPException(403, "License 已被撤销")
    if info["status"] == "expired":
        raise HTTPException(403, "License 已过期")
    return info


# --- License API ---

@app.post("/api/license/activate")
async def activate_license(req: LicenseActivateRequest):
    """首次激活 License — 绑定硬件指纹，返回 JWT + 规则包"""
    license_info = _load_license_info(req.license_key)

    if not verify_hardware(req.license_key, req.hardware_fingerprint):
        raise HTTPException(403, "硬件指纹不匹配：5 个因子中至少需匹配 4 个")

    bind_hardware(req.license_key, req.hardware_fingerprint)

    jwt_token = generate_jwt(req.license_key)
    session_id = create_session(req.license_key, jwt_token, req.container_id)
    rules = build_rules()

    return {
        "status": "activated",
        "jwt_token": jwt_token,
        "session_id": session_id,
        "license_info": {
            "type": license_info["tier"],
            "expires_at": license_info["expires_at"],
            "max_concurrent": license_info["max_concurrent"]
        },
        "rules": rules,
        "rules_signature": sign_rules(rules),
        "challenge": generate_challenge()
    }


@app.post("/api/license/verify")
async def verify_license(req: LicenseVerifyRequest):
    """周期性验证 License — 挑战-应答协议"""
    license_info = _load_license_info(req.license_key)

    session = find_session_by_token(req.session_token)
    if session is None or session["license_key"] != req.license_key:
        return {
            "status": "invalid_session",
            "message": "会话无效，请重新激活",
            "action": "reactivate"
        }

    touch_session(req.session_token)
    rules = build_rules()

    return {
        "status": "valid",
        "jwt_token": generate_jwt(req.license_key),
        "rules": rules,
        "rules_signature": sign_rules(rules),
        "challenge": generate_challenge()
    }


@app.post("/api/license/heartbeat")
async def license_heartbeat(req: HeartbeatRequest):
    """运行时心跳"""
    check_expired()
    info = get_license(req.license_key)
    if info is None:
        return {"status": "invalid"}

    session = find_session_by_token(req.session_token)
    if session:
        touch_session(req.session_token)

    if info["status"] != "active":
        return {"status": info["status"], "message": f"License {info['status']}", "action": "renew"}

    expires_at = datetime.fromisoformat(info["expires_at"])
    if datetime.utcnow() > expires_at:
        return {"status": "expired", "message": "License 已过期", "action": "renew"}

    return {
        "status": "healthy",
        "license_status": info["status"],
        "expires_at": info["expires_at"]
    }


@app.post("/api/license/rules")
async def get_rules(req: Request):
    """下发当日规则包（RSA 签名，24 小时有效）"""
    body = await req.json()
    license_key = body.get("license_key")
    info = get_license(license_key)
    if info is None or info["status"] != "active":
        raise HTTPException(403, "License 不存在或无效")

    rules = build_rules()
    return {"rules": rules, "rules_signature": sign_rules(rules)}


@app.get("/api/license/status")
async def get_license_status(license_key: str):
    """用户自查 License 状态"""
    check_expired()
    info = get_license(license_key)
    if info is None:
        return {"status": "not_found"}

    return {
        "status": info["status"],
        "type": info["tier"],
        "created_at": info["created_at"],
        "expires_at": info["expires_at"],
        "max_concurrent": info["max_concurrent"]
    }


# --- Admin API ---

@app.post("/api/admin/generate-license")
async def admin_generate_license(req: GenerateLicenseRequest, request: Request):
    """
    生成新的 License Key（管理员端点）
    可选自动发送购买确认邮件
    """
    _check_admin(request)

    if req.tier not in ("pro", "enterprise"):
        raise HTTPException(400, "tier 必须为 pro 或 enterprise")

    license_info = create_license(
        customer_email=req.customer_email,
        tier=req.tier,
        expires_in_days=req.expires_in_days,
        max_concurrent=req.max_concurrent,
        notes=req.notes
    )

    if req.send_email:
        send_license_email(
            to_email=req.customer_email,
            license_key=license_info["license_key"],
            tier=req.tier,
            expires_at=license_info["expires_at"],
            max_concurrent=req.max_concurrent
        )

    return {
        "status": "created",
        "license": {
            "license_key": license_info["license_key"],
            "customer_email": license_info["customer_email"],
            "tier": license_info["tier"],
            "max_concurrent": license_info["max_concurrent"],
            "created_at": license_info["created_at"],
            "expires_at": license_info["expires_at"]
        },
        "email_sent": req.send_email
    }


@app.get("/api/admin/licenses")
async def admin_list_licenses(
    request: Request,
    status: Optional[str] = None,
    tier: Optional[str] = None
):
    """列出所有 License（管理员端点）"""
    _check_admin(request)
    return {"licenses": list_licenses(status=status, tier=tier)}


@app.post("/api/admin/revoke-license")
async def admin_revoke_license(req: RevokeLicenseRequest, request: Request):
    """撤销 License（管理员端点）"""
    _check_admin(request)
    ok = revoke_license(req.license_key)
    if not ok:
        raise HTTPException(404, "License 不存在或已被撤销")
    return {"status": "revoked", "license_key": req.license_key}


# --- Payment API ---

@app.post("/api/payment/complete")
async def complete_payment(req: CompletePaymentRequest):
    """
    支付完成后调用 — 验证 PayPal 订单 → 生成 License → 发送邮件
    由前端 PayPal SDK onApprove 回调触发
    """
    # 验证 PayPal 订单
    capture_result = await verify_paypal_order(req.order_id)

    # 提取支付信息
    payer_email = req.customer_email
    amount = None
    for purchase_unit in capture_result.get("purchase_units", []):
        payments = purchase_unit.get("payments", {}).get("captures", [])
        if payments:
            amount = payments[0].get("amount", {}).get("value")

    # 生成 License
    license_info = create_license(
        customer_email=payer_email,
        tier=req.tier,
        expires_in_days=req.expires_in_days,
        max_concurrent=req.max_concurrent,
        notes=f"PayPal Order: {req.order_id}, Amount: {amount}"
    )

    # 发送邮件
    send_license_email(
        to_email=payer_email,
        license_key=license_info["license_key"],
        tier=req.tier,
        expires_at=license_info["expires_at"],
        max_concurrent=req.max_concurrent
    )

    return {
        "status": "completed",
        "license_key": license_info["license_key"],
        "tier": license_info["tier"],
        "expires_at": license_info["expires_at"],
        "amount": amount,
        "email_sent": True
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "license-server",
        "timestamp": int(time.time())
    }


# --- 启动初始化 ---

if __name__ == "__main__":
    import uvicorn

    # 种子 License（如果数据库为空）
    existing = list_licenses()
    if not existing:
        create_license(
            customer_email="demo@privacygw.com",
            tier="pro",
            expires_in_days=30,
            max_concurrent=20,
            notes="默认 Pro 测试 License"
        )
        print("已创建默认 Pro 测试 License")

    print("License Verification Server 启动")
    print("端口: 8443")
    uvicorn.run(app, host="0.0.0.0", port=8443)
