import json
import os
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

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
                    person_count INTEGER DEFAULT 0,
                    location_count INTEGER DEFAULT 0,
                    org_count INTEGER DEFAULT 0,
                    plate_count INTEGER DEFAULT 0,
                    ip_count INTEGER DEFAULT 0,
                    url_count INTEGER DEFAULT 0,
                    date_count INTEGER DEFAULT 0,
                    amount_count INTEGER DEFAULT 0,
                    postcode_count INTEGER DEFAULT 0,
                    total_count INTEGER DEFAULT 0
                );
                
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    action TEXT NOT NULL,
                    detail_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_log(session_id);
                CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action);
                CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_log(created_at);
                
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT NOT NULL,
                    attempt_count INTEGER DEFAULT 0,
                    locked_until TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_login_ip ON login_attempts(ip_address);
            """)

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

    def log_audit(self, session_id: Optional[str], action: str, detail: Optional[Dict] = None):
        """记录审计日志"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            detail_json = json.dumps(detail) if detail else None
            cursor.execute(
                "INSERT INTO audit_log (session_id, action, detail_json) VALUES (?, ?, ?)",
                (session_id, action, detail_json)
            )
        logger.debug(f"审计日志: action={action}, session_id={session_id}")

    def check_login_attempt(self, ip_address: str) -> Tuple[bool, Optional[int]]:
        """
        检查登录尝试情况
        返回: (是否锁定, 剩余尝试次数)
        """
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM login_attempts WHERE ip_address = ?", (ip_address,))
            row = cursor.fetchone()
            
            now = datetime.now()
            
            if not row:
                return False, 5
            
            locked_until = None
            if row["locked_until"]:
                try:
                    locked_until = datetime.fromisoformat(row["locked_until"])
                except:
                    pass
            
            if locked_until and now < locked_until:
                return True, 0
            
            attempt_count = row["attempt_count"]
            remaining = max(0, 5 - attempt_count)
            return False, remaining

    def record_login_attempt(self, ip_address: str, success: bool):
        """记录登录尝试"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            now = datetime.now()
            
            cursor.execute("SELECT * FROM login_attempts WHERE ip_address = ?", (ip_address,))
            row = cursor.fetchone()
            
            if success:
                if row:
                    cursor.execute(
                        "DELETE FROM login_attempts WHERE ip_address = ?",
                        (ip_address,)
                    )
            else:
                if row:
                    new_count = row["attempt_count"] + 1
                    if new_count >= 5:
                        locked_until = (now + timedelta(minutes=15)).isoformat()
                        cursor.execute(
                            "UPDATE login_attempts SET attempt_count = ?, locked_until = ?, updated_at = ? WHERE ip_address = ?",
                            (new_count, locked_until, now.isoformat(), ip_address)
                        )
                    else:
                        cursor.execute(
                            "UPDATE login_attempts SET attempt_count = ?, updated_at = ? WHERE ip_address = ?",
                            (new_count, now.isoformat(), ip_address)
                        )
                else:
                    cursor.execute(
                        "INSERT INTO login_attempts (ip_address, attempt_count) VALUES (?, 1)",
                        (ip_address,)
                    )

    def update_stats(self, stats: Dict[str, int]):
        today = datetime.now().strftime("%Y-%m-%d")
        
        # 处理 organization 到 org 的映射
        normalized_stats = stats.copy()
        if "organization" in normalized_stats:
            normalized_stats["org"] = normalized_stats.get("org", 0) + normalized_stats["organization"]
            del normalized_stats["organization"]
        
        with self.get_conn() as conn:
            cursor = conn.cursor()
            
            # 构建更新语句
            set_clauses = []
            old_fields = ["phone", "email", "idcard", "bankcard", "custom"]
            new_fields = ["person", "location", "org", "plate", "ip", "url", "date", "amount", "postcode"]

            update_params = []
            for data_type, count in normalized_stats.items():
                if count <= 0:
                    continue
                column = f"{data_type}_count"
                set_clauses.append(f"{column} = {column} + ?")
                update_params.append(count)

            if not set_clauses:
                return

            sql = f"""
                INSERT INTO stats (date, {', '.join([f"{f}_count" for f in old_fields + new_fields])}, total_count)
                VALUES (?, {', '.join(['?'] * (len(old_fields + new_fields) + 1))})
                ON CONFLICT(date) DO UPDATE SET
                {', '.join(set_clauses)},
                total_count = total_count + ?
            """

            insert_values = [today]
            for f in old_fields + new_fields:
                insert_values.append(normalized_stats.get(f, 0))
            insert_values.append(sum(normalized_stats.values()))

            all_params = insert_values + update_params + [sum(normalized_stats.values())]
            cursor.execute(sql, all_params)

    def get_today_stats(self) -> Dict:
        today = datetime.now().strftime("%Y-%m-%d")
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM stats WHERE date = ?
            """, (today,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return {
                "date": today,
                "phone_count": 0,
                "email_count": 0,
                "idcard_count": 0,
                "bankcard_count": 0,
                "custom_count": 0,
                "person_count": 0,
                "location_count": 0,
                "org_count": 0,
                "plate_count": 0,
                "ip_count": 0,
                "url_count": 0,
                "date_count": 0,
                "amount_count": 0,
                "postcode_count": 0,
                "total_count": 0
            }


db = Database()
