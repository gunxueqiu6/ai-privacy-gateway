import json
import os
import hashlib
import logging
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Generator, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "./vault_data/privacy_vault.db")

ALLOWED_STATS_COLUMNS = frozenset({
    "phone", "email", "idcard", "bankcard", "custom",
    "person", "location", "org", "plate", "ip",
    "url", "date", "amount", "postcode", "total",
})

class Database:
    def __init__(self, db_path: Optional[str] = None) -> None:
        self.db_path = db_path or DB_PATH
        self._ensure_dir()
        self._init_db()

    def _ensure_dir(self) -> None:
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

    @contextmanager
    def get_conn(self) -> Generator[sqlite3.Connection, None, None]:
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

    @contextmanager
    def _exclusive_conn(self) -> Generator[sqlite3.Connection, None, None]:
        """获取具有排他写锁的数据库连接（BEGIN IMMEDIATE），用于原子操作"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS licenses (
                    id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL UNIQUE,
                    tier TEXT NOT NULL,
                    seats INTEGER NOT NULL,
                    email TEXT,
                    issued_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    jwt_token TEXT NOT NULL,
                    payment_id TEXT,
                    revoked INTEGER DEFAULT 0
                );

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

                -- Phase 3: Multi-user and team tables
                CREATE TABLE IF NOT EXISTS teams (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    license_id TEXT,
                    created_at TEXT NOT NULL,
                    settings TEXT DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    team_id TEXT NOT NULL,
                    username TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'member',
                    api_key TEXT UNIQUE,
                    created_at TEXT NOT NULL,
                    last_login_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    UNIQUE(team_id, username)
                );

                CREATE INDEX IF NOT EXISTS idx_users_team ON users(team_id);
                CREATE INDEX IF NOT EXISTS idx_users_api_key ON users(api_key);

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );

                CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
                CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            """)

            # Migrate existing audit_log table to add prev_hash column
            cursor.execute("PRAGMA table_info(audit_log)")
            audit_columns = {row[1] for row in cursor.fetchall()}
            if "prev_hash" not in audit_columns:
                cursor.execute("ALTER TABLE audit_log ADD COLUMN prev_hash TEXT")
                logger.info("已为 audit_log 表添加 prev_hash 列")

            # Phase 3: Add team_id columns to existing tables
            cursor.execute("PRAGMA table_info(vault_mappings)")
            vm_cols = {row[1] for row in cursor.fetchall()}
            if "team_id" not in vm_cols:
                cursor.execute("ALTER TABLE vault_mappings ADD COLUMN team_id TEXT DEFAULT 'default'")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_vault_team_session ON vault_mappings(team_id, session_id)")
                logger.info("Added team_id column to vault_mappings")

            cursor.execute("PRAGMA table_info(custom_keywords)")
            ck_cols = {row[1] for row in cursor.fetchall()}
            if "team_id" not in ck_cols:
                cursor.execute("ALTER TABLE custom_keywords ADD COLUMN team_id TEXT DEFAULT 'default'")
                logger.info("Added team_id column to custom_keywords")

            cursor.execute("PRAGMA table_info(stats)")
            st_cols = {row[1] for row in cursor.fetchall()}
            if "team_id" not in st_cols:
                cursor.execute("ALTER TABLE stats ADD COLUMN team_id TEXT DEFAULT 'default'")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_stats_team_date ON stats(team_id, date)")
                logger.info("Added team_id column to stats")

            # Phase 4: OAuth columns
            cursor.execute("PRAGMA table_info(users)")
            usr_cols = {row[1] for row in cursor.fetchall()}
            if "email" not in usr_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN email TEXT DEFAULT ''")
                logger.info("Added email column to users")
            if "oauth_provider" not in usr_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN oauth_provider TEXT")
                logger.info("Added oauth_provider column to users")
            if "oauth_id" not in usr_cols:
                cursor.execute("ALTER TABLE users ADD COLUMN oauth_id TEXT")
                logger.info("Added oauth_id column to users")
            if "oauth_provider" in usr_cols and "oauth_id" in usr_cols:
                # Create index for OAuth lookups if not exists
                cursor.execute("PRAGMA index_list(users)")
                idx_list = {row[2] for row in cursor.fetchall()}
                if "idx_users_oauth" not in idx_list:
                    cursor.execute(
                        "CREATE INDEX IF NOT EXISTS idx_users_oauth ON users(oauth_provider, oauth_id)"
                    )
                    logger.info("Created idx_users_oauth index")

    def save_mappings(self, session_id: str, mappings: Dict[str, str], data_type: str = "unknown", team_id: Optional[str] = None) -> None:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            for placeholder, real_value in mappings.items():
                cursor.execute(
                    "INSERT INTO vault_mappings (session_id, placeholder, real_value, data_type, team_id) VALUES (?, ?, ?, ?, COALESCE(?, 'default'))",
                    (session_id, placeholder, real_value, data_type, team_id)
                )
        logger.info(f"保存 {len(mappings)} 条映射记录")

    def cleanup_expired_mappings(self, retention_hours: int = 72) -> int:
        """清理超过保留时长的映射记录"""
        cutoff = (datetime.utcnow() - timedelta(hours=retention_hours)).strftime("%Y-%m-%d %H:%M:%S")
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vault_mappings WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"清理了 {deleted} 条过期映射记录 (保留 {retention_hours} 小时)")
        return deleted

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

    def clear_session(self, session_id: str) -> None:
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

    def clear_all_mappings(self) -> None:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vault_mappings")

    def log_audit(self, session_id: Optional[str], action: str, detail: Optional[Dict[str, Any]] = None) -> None:
        """记录审计日志（哈希链完整性保护）"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            detail_json = json.dumps(detail) if detail else None

            # 获取最后一条审计记录，构建哈希链
            cursor.execute(
                "SELECT id, session_id, action, detail_json, created_at, prev_hash "
                "FROM audit_log ORDER BY id DESC LIMIT 1"
            )
            last = cursor.fetchone()

            if last:
                prev_content = "|".join(str(v) for v in [
                    last['prev_hash'] or '',
                    last['session_id'] or '',
                    last['action'],
                    last['detail_json'] or '',
                    last['created_at'] or ''
                ])
                prev_hash = hashlib.sha256(prev_content.encode('utf-8')).hexdigest()
            else:
                prev_hash = None

            now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                "INSERT INTO audit_log (session_id, action, detail_json, created_at, prev_hash) VALUES (?, ?, ?, ?, ?)",
                (session_id, action, detail_json, now, prev_hash)
            )
        logger.debug(f"审计日志: action={action}, session_id={session_id}")

    def verify_audit_integrity(self) -> bool:
        """验证审计日志哈希链完整性"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, session_id, action, detail_json, created_at, prev_hash "
                "FROM audit_log ORDER BY id ASC"
            )
            rows = cursor.fetchall()

            if len(rows) <= 1:
                return True

            intact = True
            for i in range(1, len(rows)):
                prev = rows[i - 1]
                curr = rows[i]

                prev_content = "|".join(str(v) for v in [
                    prev['prev_hash'] or '',
                    prev['session_id'] or '',
                    prev['action'],
                    prev['detail_json'] or '',
                    prev['created_at'] or ''
                ])
                expected_hash = hashlib.sha256(prev_content.encode('utf-8')).hexdigest()

                if curr['prev_hash'] is not None and curr['prev_hash'] != expected_hash:
                    logger.warning(f"审计日志哈希链断裂: id={curr['id']} prev_hash 不匹配")
                    intact = False

            if intact:
                logger.info("审计日志完整性验证通过")
            else:
                logger.error("审计日志完整性验证失败 — 可能存在篡改")

            return intact

    def check_login_attempt(self, ip_address: str) -> Tuple[bool, Optional[int]]:
        """
        检查登录尝试情况
        返回: (是否锁定, 剩余尝试次数)
        """
        with self._exclusive_conn() as conn:
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
                except (ValueError, TypeError):
                    pass

            if locked_until and now < locked_until:
                return True, 0

            attempt_count = row["attempt_count"]
            remaining = max(0, 5 - attempt_count)
            return False, remaining

    def record_login_attempt(self, ip_address: str, success: bool) -> None:
        """记录登录尝试"""
        with self._exclusive_conn() as conn:
            cursor = conn.cursor()
            now = datetime.now()

            # 在同一个 IMMEDIATE 事务中读取并写入，防止竞态条件
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

    def update_stats(self, stats: Dict[str, int]) -> None:
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
                if data_type not in ALLOWED_STATS_COLUMNS:
                    logger.warning(f"跳过未知统计字段: {data_type}")
                    continue
                column = f"{data_type}_count"
                set_clauses.append(f"{column} = {column} + ?")
                update_params.append(count)

            if not set_clauses:
                return

            # nosec B608 — columns from ALLOWED_STATS_COLUMNS allowlist
            sql = f"""
                INSERT INTO stats (date, {', '.join([f"{f}_count" for f in old_fields + new_fields])}, total_count)
                VALUES (?, {', '.join(['?'] * (len(old_fields + new_fields) + 1))})
                ON CONFLICT(date) DO UPDATE SET
                {', '.join(set_clauses)},
                total_count = total_count + ?
            """

            insert_values: List[Any] = [today]
            for f in old_fields + new_fields:
                insert_values.append(normalized_stats.get(f, 0))
            insert_values.append(sum(normalized_stats.values()))

            all_params = insert_values + update_params + [sum(normalized_stats.values())]
            cursor.execute(sql, all_params)

    def get_today_stats(self) -> Dict[str, Any]:
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



    def save_license(
        self,
        license_id: str,
        team_id: str,
        tier: str,
        seats: int,
        email: str,
        issued_at: str,
        expires_at: str,
        jwt_token: str,
        payment_id: Optional[str] = None,
    ) -> None:
        """Save a new license record."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR REPLACE INTO licenses
                   (id, team_id, tier, seats, email, issued_at, expires_at, jwt_token, payment_id, revoked)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                (license_id, team_id, tier, seats, email, issued_at, expires_at, jwt_token, payment_id),
            )

    def get_license_by_team(self, team_id: str) -> Optional[Dict[str, Any]]:
        """Get the active license for a team."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM licenses
                   WHERE team_id = ? AND revoked = 0
                   ORDER BY issued_at DESC LIMIT 1""",
                (team_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def revoke_license(self, team_id: str) -> bool:
        """Revoke a team's license."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE licenses SET revoked = 1 WHERE team_id = ? AND revoked = 0",
                (team_id,),
            )
            return cursor.rowcount > 0

    def is_token_revoked(self, team_id: str) -> bool:
        """Check if a team's license has been revoked."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT revoked FROM licenses WHERE team_id = ? ORDER BY issued_at DESC LIMIT 1",
                (team_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return False
            return bool(row["revoked"])

    def get_license_count(self) -> int:
        """Get count of active (non-revoked) licenses."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as cnt FROM licenses WHERE revoked = 0")
            row = cursor.fetchone()
            return row["cnt"] if row else 0


class EncryptedVault:
    """Enterprise encrypted storage for vault mappings using AES-GCM."""
    
    def __init__(self, key: Optional[bytes] = None) -> None:
        if key:
            self._key = key
        else:
            import os as _os
            key_env = _os.environ.get("VAULT_ENCRYPTION_KEY", "")
            if key_env:
                import base64
                self._key = base64.b64decode(key_env)
            else:
                self._key = None
    
    @property
    def available(self) -> bool:
        return self._key is not None
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext using AES-GCM. Returns base64-encoded ciphertext."""
        if not self.available:
            return plaintext
        import os as _os
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        
        aesgcm = AESGCM(self._key)
        nonce = _os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
        # Combine nonce + ciphertext and base64 encode
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode()
    
    def decrypt(self, ciphertext_b64: str) -> str:
        """Decrypt base64-encoded ciphertext back to plaintext."""
        if not self.available:
            return ciphertext_b64
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        import base64
        
        aesgcm = AESGCM(self._key)
        combined = base64.b64decode(ciphertext_b64)
        nonce = combined[:12]
        ciphertext = combined[12:]
        return aesgcm.decrypt(nonce, ciphertext, None).decode()


# Global encrypted vault instance
encrypted_vault = EncryptedVault()

db = Database()

