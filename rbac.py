"""
RBAC 权限控制模块 - Enterprise 版
角色：超级管理员 / 审计员 / 普通用户
用户数据持久化到数据库，会话令牌保留在内存
"""
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class Role(Enum):
    """角色定义"""
    SUPER_ADMIN = "super_admin"   # 超级管理员：全部权限
    AUDITOR = "auditor"           # 审计员：查看日志、统计
    USER = "user"                 # 普通用户：基础功能


class Permission(Enum):
    """权限定义"""
    # 管理权限
    MANAGE_USERS = "manage_users"         # 用户管理
    MANAGE_KEYWORDS = "manage_keywords"   # 敏感词管理
    MANAGE_SETTINGS = "manage_settings"   # 系统设置
    MANAGE_LICENSE = "manage_license"     # License 管理

    # 查看权限
    VIEW_STATS = "view_stats"             # 查看统计
    VIEW_LOGS = "view_logs"               # 查看审计日志
    VIEW_SESSIONS = "view_sessions"       # 查看会话

    # 操作权限
    CLEAR_DATA = "clear_data"             # 清除数据
    EXPORT_DATA = "export_data"           # 导出数据
    SEND_ALERT = "send_alert"             # 发送告警


# 角色权限映射
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.SUPER_ADMIN: set(Permission),  # 全部权限
    Role.AUDITOR: {
        Permission.VIEW_STATS,
        Permission.VIEW_LOGS,
        Permission.VIEW_SESSIONS,
        Permission.EXPORT_DATA,
    },
    Role.USER: {
        Permission.VIEW_STATS,
    },
}


class User:
    """用户模型"""

    def __init__(
        self,
        user_id: str,
        username: str,
        role: Role,
        password_hash: str,
        created_at: str,
        last_login: Optional[str] = None,
        is_active: bool = True
    ):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.password_hash = password_hash
        self.created_at = created_at
        self.last_login = last_login
        self.is_active = is_active

    def has_permission(self, permission: Permission) -> bool:
        """检查权限"""
        return permission in ROLE_PERMISSIONS[self.role]

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role.value,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": self.is_active
        }

    @staticmethod
    def from_db_row(row: Dict) -> "User":
        """从数据库行创建 User 对象"""
        return User(
            user_id=row["user_id"],
            username=row["username"],
            role=Role(row["role"]),
            password_hash=row["password_hash"],
            created_at=row["created_at"],
            last_login=row.get("last_login"),
            is_active=bool(row.get("is_active", 1))
        )


class RBACManager:
    """RBAC 权限管理器 — 用户持久化到数据库，会话令牌在内存"""

    def __init__(self):
        self.sessions: Dict[str, str] = {}  # session_token -> user_id (内存)
        self._init_default_users()

    def _hash_password(self, password: str) -> str:
        """哈希密码 - 使用 database.py 中的 bcrypt"""
        db = self._get_db()
        return db.hash_password(password)

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码 - 支持旧 SHA-256 和新 bcrypt"""
        db = self._get_db()
        return db.verify_password(password, stored_hash)

    def _generate_token(self, user_id: str) -> str:
        """生成会话令牌"""
        import hashlib
        return hashlib.sha256(f"{user_id}_{time.time()}".encode()).hexdigest()

    def _get_db(self):
        """获取数据库实例"""
        from database import db
        return db

    def _init_default_users(self):
        """初始化默认用户（仅当数据库为空时）"""
        db = self._get_db()
        existing = db.get_all_rbac_users()
        if existing:
            logger.info(f"[RBAC] 从数据库加载了 {len(existing)} 个用户")
            return

        # 创建默认用户
        now = datetime.now().isoformat()
        db.create_rbac_user("admin", "admin", Role.SUPER_ADMIN.value, self._hash_password("admin123"), now)
        db.create_rbac_user("auditor", "auditor", Role.AUDITOR.value, self._hash_password("audit123"), now)
        logger.info("[RBAC] 默认用户已创建并持久化到数据库")

    def authenticate(self, username: str, password: str) -> Optional[str]:
        """认证用户 - 支持密码自动升级"""
        db = self._get_db()
        row = db.get_rbac_user_by_username(username)
        if not row or not row["is_active"]:
            logger.warning(f"[RBAC] 用户 {username} 不存在或已禁用")
            return None

        # 验证密码（支持旧 SHA-256 和新 bcrypt）
        if not self._verify_password(password, row["password_hash"]):
            logger.warning(f"[RBAC] 用户 {username} 密码验证失败")
            return None

        # 如果密码是旧格式，自动升级到 bcrypt
        if db.needs_password_upgrade(row["password_hash"]):
            new_hash = self._hash_password(password)
            db.update_rbac_user_password(row["user_id"], new_hash)
            logger.info(f"[RBAC] 用户 {username} 密码已升级到 bcrypt")

        token = self._generate_token(row["user_id"])
        self.sessions[token] = row["user_id"]
        db.update_rbac_user_login(row["user_id"], datetime.now().isoformat())
        logger.info(f"[RBAC] 用户 {username} 登录成功")
        return token

    def logout(self, token: str):
        """登出"""
        if token in self.sessions:
            user_id = self.sessions[token]
            del self.sessions[token]
            logger.info(f"[RBAC] 用户 {user_id} 登出")

    def get_user_by_token(self, token: str) -> Optional[User]:
        """通过令牌获取用户"""
        user_id = self.sessions.get(token)
        if user_id:
            return self.get_user_by_id(user_id)
        return None

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """通过ID获取用户"""
        db = self._get_db()
        row = db.get_rbac_user_by_id(user_id)
        return User.from_db_row(row) if row else None

    def check_permission(self, token: str, permission: Permission) -> bool:
        """检查权限"""
        user = self.get_user_by_token(token)
        if user:
            return user.has_permission(permission)
        return False

    def create_user(
        self,
        username: str,
        password: str,
        role: Role,
        created_by: str
    ) -> Optional[User]:
        """创建用户"""
        # 检查权限
        creator = self.get_user_by_id(created_by)
        if not creator or not creator.has_permission(Permission.MANAGE_USERS):
            logger.warning(f"[RBAC] 用户 {created_by} 无权限创建用户")
            return None

        db = self._get_db()
        existing = db.get_rbac_user_by_username(username)
        if existing:
            logger.warning(f"[RBAC] 用户名 {username} 已存在")
            return None

        user_id = f"user_{int(time.time() * 1000)}"
        now = datetime.now().isoformat()
        if db.create_rbac_user(user_id, username, role.value, self._hash_password(password), now):
            logger.info(f"[RBAC] 用户 {username} 创建成功，角色 {role.value}")
            return User(user_id, username, role, self._hash_password(password), now)
        return None

    def delete_user(self, user_id: str, deleted_by: str) -> bool:
        """删除用户"""
        deleter = self.get_user_by_id(deleted_by)
        if not deleter or not deleter.has_permission(Permission.MANAGE_USERS):
            return False

        db = self._get_db()
        if db.delete_rbac_user(user_id):
            logger.info(f"[RBAC] 用户 {user_id} 已删除")
            return True
        return False

    def update_role(self, user_id: str, new_role: Role, updated_by: str) -> bool:
        """更新角色"""
        updater = self.get_user_by_id(updated_by)
        if not updater or not updater.has_permission(Permission.MANAGE_USERS):
            return False

        db = self._get_db()
        if db.update_rbac_user_role(user_id, new_role.value):
            logger.info(f"[RBAC] 用户 {user_id} 角色更新为 {new_role.value}")
            return True
        return False

    def list_users(self) -> List[Dict]:
        """列出用户"""
        db = self._get_db()
        rows = db.get_all_rbac_users()
        return [User.from_db_row(r).to_dict() for r in rows]

    def get_roles(self) -> List[str]:
        """获取角色列表"""
        return [role.value for role in Role]

    def get_permissions(self, role: Role) -> List[str]:
        """获取角色的权限列表"""
        return [p.value for p in ROLE_PERMISSIONS.get(role, set())]


# 全局 RBAC 管理器实例
rbac_manager: Optional[RBACManager] = None


def get_rbac_manager() -> RBACManager:
    """获取 RBAC 管理器实例"""
    global rbac_manager
    if rbac_manager is None:
        rbac_manager = RBACManager()
    return rbac_manager
