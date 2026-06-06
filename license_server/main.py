"""
License 验证服务器 - Pro/Enterprise 版授权管理
部署在 VPS 上，处理激活、验证、规则下发
"""
import hashlib
import json
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# 配置
LICENSE_DB_PATH = "./license_data/licenses.db"
RULES_SIGNING_KEY = "your_rsa_private_key_here"  # 实际使用 RSA 密钥

app = FastAPI(title="License Verification Server")

# 模拟数据库（实际应使用 SQLite/PostgreSQL）
licenses_db: Dict[str, Dict] = {}
hardware_bindings: Dict[str, Dict] = {}
active_sessions: Dict[str, Dict] = {}


class LicenseActivateRequest(BaseModel):
    license_key: str
    hardware_fingerprint: Dict[str, str]  # {主板序列号, 磁盘UUID, MAC地址, 容器ID}
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


def generate_challenge() -> str:
    """生成随机挑战码"""
    return hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:32]


def verify_hardware_fingerprint(license_key: str, fingerprint: Dict[str, str]) -> bool:
    """验证硬件指纹（5因子中至少匹配4个）"""
    if license_key not in hardware_bindings:
        return True  # 首次激活，自动绑定

    stored = hardware_bindings[license_key]
    match_count = 0

    for key in ["board_serial", "disk_uuid", "mac_address", "container_id", "hostname"]:
        if stored.get(key) == fingerprint.get(key):
            match_count += 1

    return match_count >= 4  # 至少匹配4个


def sign_rules(rules: Dict) -> str:
    """签名规则包（实际使用 RSA）"""
    # 模拟签名
    rules_json = json.dumps(rules, sort_keys=True)
    signature = hashlib.sha256(f"{RULES_SIGNING_KEY}{rules_json}".encode()).hexdigest()
    return signature


def generate_jwt(license_key: str, expires_hours: int = 1) -> str:
    """生成 JWT token（模拟）"""
    payload = {
        "license_key": license_key,
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + expires_hours * 3600
    }
    token = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return f"jwt_{token}"


@app.post("/api/license/activate")
async def activate_license(req: LicenseActivateRequest):
    """
    首次激活 License
    绑定硬件指纹，返回 JWT + 规则包
    """
    license_key = req.license_key

    # 检查 License 是否存在
    if license_key not in licenses_db:
        # 模拟：自动创建 Pro License
        licenses_db[license_key] = {
            "type": "pro",
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            "max_concurrent": 20
        }

    license_info = licenses_db[license_key]

    # 检查 License 状态
    if license_info["status"] != "active":
        raise HTTPException(403, "License 已过期或被禁用")

    # 验证硬件指纹
    if not verify_hardware_fingerprint(license_key, req.hardware_fingerprint):
        raise HTTPException(403, "硬件指纹不匹配")

    # 绑定硬件指纹
    hardware_bindings[license_key] = req.hardware_fingerprint

    # 生成 JWT
    jwt_token = generate_jwt(license_key)

    # 创建会话
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    active_sessions[session_id] = {
        "license_key": license_key,
        "container_id": req.container_id,
        "jwt_token": jwt_token,
        "last_heartbeat": datetime.now().isoformat()
    }

    # 生成规则包
    rules = {
        "mask_patterns": {
            "phone": r'\b(1[3-9]\d{9})\b',
            "email": r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            "idcard": r'\b([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])\b',
            "bankcard": r'\b([1-9]\d{15,18})\b'
        },
        "custom_keywords": ["密码", "密钥", "token"],
        "version": "2026.1",
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 86400  # 24小时有效
    }

    rules_signature = sign_rules(rules)

    return {
        "status": "activated",
        "jwt_token": jwt_token,
        "session_id": session_id,
        "license_info": {
            "type": license_info["type"],
            "expires_at": license_info["expires_at"],
            "max_concurrent": license_info["max_concurrent"]
        },
        "rules": rules,
        "rules_signature": rules_signature,
        "challenge": generate_challenge()
    }


@app.post("/api/license/verify")
async def verify_license(req: LicenseVerifyRequest):
    """
    周期性验证 License
    挑战-应答协议
    """
    license_key = req.license_key

    # 检查 License
    if license_key not in licenses_db:
        raise HTTPException(403, "License 不存在")

    license_info = licenses_db[license_key]

    if license_info["status"] != "active":
        return {
            "status": "expired",
            "message": "License 已过期",
            "action": "renew"
        }

    # 验证 JWT
    jwt_token = req.session_token
    session_found = False
    for session_id, session in active_sessions.items():
        if session["jwt_token"] == jwt_token and session["license_key"] == license_key:
            session_found = True
            session["last_heartbeat"] = datetime.now().isoformat()
            break

    if not session_found:
        return {
            "status": "invalid_session",
            "message": "会话无效，请重新激活",
            "action": "reactivate"
        }

    # 返回新规则包
    rules = {
        "mask_patterns": {
            "phone": r'\b(1[3-9]\d{9})\b',
            "email": r'\b([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b',
            "idcard": r'\b([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])\b',
            "bankcard": r'\b([1-9]\d{15,18})\b'
        },
        "custom_keywords": ["密码", "密钥", "token", "API_KEY"],
        "version": "2026.1",
        "issued_at": int(time.time()),
        "expires_at": int(time.time()) + 86400
    }

    return {
        "status": "valid",
        "jwt_token": generate_jwt(license_key),  # 续期 JWT
        "rules": rules,
        "rules_signature": sign_rules(rules),
        "challenge": generate_challenge()
    }


@app.post("/api/license/heartbeat")
async def license_heartbeat(req: HeartbeatRequest):
    """
    运行时心跳
    检测 License 状态，上报健康信息
    """
    license_key = req.license_key

    if license_key not in licenses_db:
        return {"status": "invalid"}

    license_info = licenses_db[license_key]

    # 更新心跳时间
    for session_id, session in active_sessions.items():
        if session["jwt_token"] == req.session_token:
            session["last_heartbeat"] = datetime.now().isoformat()
            break

    # 检查过期
    expires_at = datetime.fromisoformat(license_info["expires_at"])
    if datetime.now() > expires_at:
        return {
            "status": "expired",
            "message": "License 已过期",
            "action": "renew"
        }

    return {
        "status": "healthy",
        "license_status": license_info["status"],
        "expires_at": license_info["expires_at"]
    }


@app.post("/api/license/rules")
async def get_rules(req: Request):
    """
    下发当日规则包
    RSA 签名，24小时有效
    """
    body = await req.json()
    license_key = body.get("license_key")

    if license_key not in licenses_db:
        raise HTTPException(403, "License 不存在")

    rules = {
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

    return {
        "rules": rules,
        "rules_signature": sign_rules(rules)
    }


@app.get("/api/license/status")
async def get_license_status(license_key: str):
    """
    用户自查 License 状态
    """
    if license_key not in licenses_db:
        return {"status": "not_found"}

    license_info = licenses_db[license_key]

    return {
        "status": license_info["status"],
        "type": license_info["type"],
        "created_at": license_info["created_at"],
        "expires_at": license_info["expires_at"],
        "max_concurrent": license_info["max_concurrent"]
    }


if __name__ == "__main__":
    import uvicorn

    # 初始化测试 License
    licenses_db["pro_test_001"] = {
        "type": "pro",
        "status": "active",
        "created_at": datetime.now().isoformat(),
        "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
        "max_concurrent": 20
    }

    print("License Verification Server 启动")
    print("端口: 8443")

    uvicorn.run(app, host="0.0.0.0", port=8443)