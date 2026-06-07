import sqlite3
import os
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Optional
from contextlib import contextmanager

try:
    import bcrypt
    HAS_BCRYPT = True
except ImportError:
    HAS_BCRYPT = False
    logger.warning("bcrypt not installed, falling back to SHA-256")

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "./vault_data/privacy_vault.db")

class Database:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS vault_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    placeholder TEXT NOT NULL,
                    real_value TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_session ON vault_mappings(session_id);
                CREATE INDEX IF NOT EXISTS idx_placeholder ON vault_mappings(placeholder);

                CREATE TABLE IF NOT EXISTS custom_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT UNIQUE NOT NULL,
                    phone_count INTEGER DEFAULT 0,
                    email_count INTEGER DEFAULT 0,
                    idcard_count INTEGER DEFAULT 0,
                    bankcard_count INTEGER DEFAULT 0,
                    custom_count INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS rbac_users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    is_active INTEGER DEFAULT 1
                );
            """)
        logger.info("✅ 数据库初始化完成")

    def save_mappings(self, session_id: str, mappings: Dict[str, str], data_type: str = "unknown"):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            for placeholder, real_value in mappings.items():
                cursor.execute(
                    "INSERT INTO vault_mappings (session_id, placeholder, real_value, data_type) VALUES (?, ?, ?, ?)",
                    (session_id, placeholder, real_value, data_type)
                )
        logger.info(f"保存 {len(mappings)} 条映射记录")

    def get_all_mappings(self) -> Dict[str, str]:
        mappings = {}
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT placeholder, real_value FROM vault_mappings")
            for row in cursor.fetchall():
                mappings[row["placeholder"]] = row["real_value"]
        return mappings

    def get_mapping(self, session_id: str, placeholder: str) -> Optional[str]:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT real_value FROM vault_mappings WHERE session_id = ? AND placeholder = ?",
                (session_id, placeholder)
            )
            row = cursor.fetchone()
            return row["real_value"] if row else None

    def clear_session(self, session_id: str):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vault_mappings WHERE session_id = ?", (session_id,))
        logger.info(f"已清除会话 {session_id} 的映射记录")

    def update_stats(self, stats: Dict[str, int]):
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            cursor = conn.cursor()
            for data_type, count in stats.items():
                if count <= 0:
                    continue
                column = f"{data_type}_count"
                cursor.execute(f"""
                    INSERT INTO stats (date, {column}, total_count)
                    VALUES (?, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET
                    {column} = {column} + ?,
                    total_count = total_count + ?
                """, (today, count, count, count, count))

    def get_today_stats(self) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, phone_count, email_count, idcard_count, bankcard_count, custom_count, total_count
                FROM stats WHERE date = ?
            """, (today,))
            row = cursor.fetchone()
            if row:
                return {
                    "date": row["date"],
                    "phone_count": row["phone_count"],
                    "email_count": row["email_count"],
                    "idcard_count": row["idcard_count"],
                    "bankcard_count": row["bankcard_count"],
                    "custom_count": row["custom_count"],
                    "total_count": row["total_count"]
                }
            return {
                "date": today,
                "phone_count": 0,
                "email_count": 0,
                "idcard_count": 0,
                "bankcard_count": 0,
                "custom_count": 0,
                "total_count": 0
            }

    def add_custom_keyword(self, keyword: str) -> bool:
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO custom_keywords (keyword) VALUES (?)", (keyword,))
            return True
        except sqlite3.IntegrityError:
            return False

    def delete_custom_keyword(self, keyword: str) -> bool:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_keywords WHERE keyword = ?", (keyword,))
            return cursor.rowcount > 0

    def get_custom_keywords(self) -> List[str]:
        keywords = []
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT keyword FROM custom_keywords")
            for row in cursor.fetchall():
                keywords.append(row["keyword"])
        return keywords

    def clear_all_mappings(self):
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vault_mappings")
        logger.info("已清除所有映射记录")

    # ---- RBAC 用户管理 ----

    def create_rbac_user(self, user_id: str, username: str, role: str, password_hash: str, created_at: str) -> bool:
        try:
            with self.get_conn() as conn:
                conn.execute(
                    "INSERT INTO rbac_users (user_id, username, role, password_hash, created_at, is_active) VALUES (?, ?, ?, ?, ?, 1)",
                    (user_id, username, role, password_hash, created_at)
                )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_rbac_user_by_id(self, user_id: str) -> Optional[Dict]:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM rbac_users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def get_rbac_user_by_username(self, username: str) -> Optional[Dict]:
        with self.get_conn() as conn:
            row = conn.execute("SELECT * FROM rbac_users WHERE username = ?", (username,)).fetchone()
            return dict(row) if row else None

    def get_all_rbac_users(self) -> List[Dict]:
        with self.get_conn() as conn:
            rows = conn.execute("SELECT * FROM rbac_users").fetchall()
            return [dict(r) for r in rows]

    def delete_rbac_user(self, user_id: str) -> bool:
        with self.get_conn() as conn:
            cursor = conn.execute("DELETE FROM rbac_users WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0

    def update_rbac_user_role(self, user_id: str, new_role: str) -> bool:
        with self.get_conn() as conn:
            cursor = conn.execute("UPDATE rbac_users SET role = ? WHERE user_id = ?", (new_role, user_id))
            return cursor.rowcount > 0

    def update_rbac_user_login(self, user_id: str, last_login: str):
        with self.get_conn() as conn:
            conn.execute("UPDATE rbac_users SET last_login = ? WHERE user_id = ?", (last_login, user_id))

    def update_rbac_user_password(self, user_id: str, new_password_hash: str):
        with self.get_conn() as conn:
            cursor = conn.execute("UPDATE rbac_users SET password_hash = ? WHERE user_id = ?", (new_password_hash, user_id))
            return cursor.rowcount > 0

    def hash_password(self, password: str) -> str:
        """使用 bcrypt 哈希密码"""
        if HAS_BCRYPT:
            return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        else:
            # 降级到 SHA-256（仅用于开发环境）
            return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """验证密码，支持旧的 SHA-256 和新的 bcrypt"""
        if self.is_old_hash(stored_hash):
            # 旧格式：纯 SHA-256
            return hashlib.sha256(password.encode('utf-8')).hexdigest() == stored_hash
        else:
            # 新格式：bcrypt
            if HAS_BCRYPT:
                return bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8'))
            return False

    def is_old_hash(self, stored_hash: str) -> bool:
        """检测是否是旧的 SHA-256 哈希（64 位十六进制）"""
        return len(stored_hash) == 64 and all(c in '0123456789abcdefABCDEF' for c in stored_hash)

    def needs_password_upgrade(self, stored_hash: str) -> bool:
        """检查密码是否需要升级（从 SHA-256 升级到 bcrypt）"""
        return self.is_old_hash(stored_hash) and HAS_BCRYPT

db = Database()
