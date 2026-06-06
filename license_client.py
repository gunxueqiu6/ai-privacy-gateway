"""
License 客户端模块 - Pro/Enterprise 版
处理激活、验证、心跳、规则更新
"""
import hashlib
import json
import os
import platform
import subprocess
import time
import uuid
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

import httpx

from config import config

logger = logging.getLogger(__name__)


class HardwareFingerprint:
    """硬件指纹采集"""

    @staticmethod
    def get_board_serial() -> str:
        """获取主板序列号"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "baseboard", "get", "serialnumber"],
                    capture_output=True, text=True
                )
                return result.stdout.strip().split("\n")[1].strip()
            else:
                result = subprocess.run(
                    ["cat", "/sys/class/dmi/id/board_serial"],
                    capture_output=True, text=True
                )
                return result.stdout.strip()
        except:
            return "unknown_board"

    @staticmethod
    def get_disk_uuid() -> str:
        """获取磁盘 UUID"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["wmic", "diskdrive", "get", "serialnumber"],
                    capture_output=True, text=True
                )
                return result.stdout.strip().split("\n")[1].strip()
            else:
                result = subprocess.run(
                    ["blkid", "-s", "UUID", "-o", "value", "/dev/sda1"],
                    capture_output=True, text=True
                )
                return result.stdout.strip()
        except:
            return "unknown_disk"

    @staticmethod
    def get_mac_address() -> str:
        """获取 MAC 地址"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ["getmac"], capture_output=True, text=True
                )
                return result.stdout.strip().split()[0]
            else:
                result = subprocess.run(
                    ["cat", "/sys/class/net/eth0/address"],
                    capture_output=True, text=True
                )
                return result.stdout.strip()
        except:
            return "unknown_mac"

    @staticmethod
    def get_hostname() -> str:
        """获取主机名"""
        return platform.node()

    @staticmethod
    def get_container_id() -> str:
        """获取 Docker 容器 ID"""
        try:
            # 检查是否在 Docker 中运行
            if os.path.exists("/proc/self/cgroup"):
                with open("/proc/self/cgroup", "r") as f:
                    content = f.read()
                    if "docker" in content:
                        # 提取容器 ID
                        lines = content.split("\n")
                        for line in lines:
                            if "docker" in line:
                                return line.split("/")[-1][:12]
            return "not_in_docker"
        except:
            return "unknown_container"

    @classmethod
    def collect(cls) -> Dict[str, str]:
        """采集完整硬件指纹"""
        return {
            "board_serial": cls.get_board_serial(),
            "disk_uuid": cls.get_disk_uuid(),
            "mac_address": cls.get_mac_address(),
            "hostname": cls.get_hostname(),
            "container_id": cls.get_container_id()
        }


class LicenseClient:
    """License 客户端"""

    def __init__(self):
        self.license_key = config.LICENSE_KEY
        self.server_url = config.LICENSE_SERVER_URL
        self.jwt_token: Optional[str] = None
        self.session_id: Optional[str] = None
        self.rules: Optional[Dict] = None
        self.rules_signature: Optional[str] = None
        self.last_verify_time: float = 0
        self.verify_failures: int = 0
        self.challenge: Optional[str] = None
        self.hardware_fingerprint = HardwareFingerprint.collect()

        # 验证状态
        self.status = "unactivated"
        self.expires_at: Optional[str] = None

    def _sign_challenge(self, challenge: str) -> str:
        """签名挑战码"""
        fingerprint_json = json.dumps(self.hardware_fingerprint, sort_keys=True)
        signature = hashlib.sha256(
            f"{self.license_key}{challenge}{fingerprint_json}".encode()
        ).hexdigest()
        return signature

    async def activate(self) -> Tuple[bool, str]:
        """
        首次激活 License
        返回: (成功与否, 消息)
        """
        if not self.server_url:
            logger.warning("License 服务器未配置，跳过激活")
            return True, "no_server"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.server_url}/api/license/activate",
                    json={
                        "license_key": self.license_key,
                        "hardware_fingerprint": self.hardware_fingerprint,
                        "container_id": self.hardware_fingerprint["container_id"],
                        "timestamp": int(time.time())
                    }
                )

                if response.status_code != 200:
                    error = response.json().get("detail", "激活失败")
                    logger.error(f"License 激活失败: {error}")
                    return False, error

                data = response.json()

                self.jwt_token = data["jwt_token"]
                self.session_id = data["session_id"]
                self.rules = data["rules"]
                self.rules_signature = data["rules_signature"]
                self.challenge = data["challenge"]
                self.status = "activated"
                self.expires_at = data["license_info"]["expires_at"]
                self.last_verify_time = time.time()
                self.verify_failures = 0

                logger.info(f"License 激活成功，有效期至 {self.expires_at}")
                return True, "activated"

        except httpx.RequestError as e:
            logger.error(f"License 激活请求失败: {e}")
            return False, str(e)

    async def verify(self) -> Tuple[bool, Dict]:
        """
        周期性验证 License
        返回: (验证成功与否, 响应数据)
        """
        if not self.server_url or not self.jwt_token:
            return True, {"status": "no_verify_needed"}

        try:
            challenge_response = self._sign_challenge(self.challenge or "")

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.server_url}/api/license/verify",
                    json={
                        "license_key": self.license_key,
                        "session_token": self.jwt_token,
                        "challenge_response": challenge_response,
                        "timestamp": int(time.time())
                    }
                )

                if response.status_code != 200:
                    self.verify_failures += 1
                    logger.warning(f"License 验证失败，累计 {self.verify_failures} 次")
                    return False, {"status": "verify_failed", "failures": self.verify_failures}

                data = response.json()

                if data["status"] == "expired":
                    self.status = "expired"
                    self.verify_failures += 1
                    return False, data

                # 更新 JWT 和规则
                self.jwt_token = data["jwt_token"]
                self.rules = data["rules"]
                self.rules_signature = data["rules_signature"]
                self.challenge = data["challenge"]
                self.last_verify_time = time.time()
                self.verify_failures = 0

                return True, data

        except httpx.RequestError as e:
            self.verify_failures += 1
            logger.warning(f"License 验证请求失败: {e}")
            return False, {"status": "network_error", "failures": self.verify_failures}

    async def heartbeat(self) -> Tuple[bool, Dict]:
        """
        发送心跳
        """
        if not self.server_url or not self.jwt_token:
            return True, {"status": "no_heartbeat_needed"}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.server_url}/api/license/heartbeat",
                    json={
                        "license_key": self.license_key,
                        "session_token": self.jwt_token,
                        "status": self.status,
                        "timestamp": int(time.time())
                    }
                )

                if response.status_code != 200:
                    return False, {"status": "heartbeat_failed"}

                data = response.json()

                if data["status"] == "expired":
                    self.status = "expired"
                    return False, data

                return True, data

        except httpx.RequestError:
            return False, {"status": "network_error"}

    def get_rules(self) -> Optional[Dict]:
        """获取当前规则包"""
        return self.rules

    def is_activated(self) -> bool:
        """检查是否已激活"""
        return self.status == "activated"

    def get_verify_failure_count(self) -> int:
        """获取验证失败次数"""
        return self.verify_failures

    def get_status(self) -> Dict:
        """获取 License 状态"""
        return {
            "license_key": self.license_key[:8] + "...",
            "status": self.status,
            "expires_at": self.expires_at,
            "verify_failures": self.verify_failures,
            "last_verify_time": self.last_verify_time,
            "hardware_fingerprint": self.hardware_fingerprint
        }


# 全局 License 客户端实例
license_client: Optional[LicenseClient] = None


def get_license_client() -> LicenseClient:
    """获取 License 客户端实例"""
    global license_client
    if license_client is None:
        license_client = LicenseClient()
    return license_client