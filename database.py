import json
import os
import hashlib
import logging
import random
import sqlite3
import time as _time
from datetime import UTC, datetime, timedelta
from typing import Dict, List, Optional, Tuple, Generator, Any
from contextlib import contextmanager

from config import config as app_config
from vault_crypto import get_vault_crypto

logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("DB_PATH", "./vault_data/privacy_vault.db")

ALLOWED_STATS_COLUMNS = frozenset({
    "phone", "email", "idcard", "bankcard", "custom",
    "person", "location", "org", "plate", "ip",
    "url", "date", "amount", "postcode", "total",
})

class Database:
    def __init__(self, db_path: Optional[str] = None, mapping_ttl: Optional[int] = None) -> None:
        self.db_path = db_path or DB_PATH
        self.mapping_ttl = mapping_ttl if mapping_ttl is not None else app_config.MAPPING_TTL
        # 无状态模式使用内存存储映射
        self._memory_mappings: Dict[str, Dict[str, str]] = {}
        # 记录每个 session 的创建时间以便基于 TTL 清理内存映射
        self._memory_mapping_times: Dict[str, datetime] = {}
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
        """获取具有排他写锁的数据库连接（BEGIN IMMEDIATE），用于原子操作

        当遇到 "database is locked" 时自动重试（最多 3 次，每次间隔 100ms + 随机抖动）。
        """
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            try:
                conn.execute("BEGIN IMMEDIATE")
            except sqlite3.OperationalError as e:
                conn.close()
                if "database is locked" in str(e) and attempt < max_retries:
                    delay = 0.1 + random.uniform(0, 0.05)
                    logger.warning("数据库锁定，重试 %d/%d (等待 %.2fs)", attempt, max_retries, delay)
                    _time.sleep(delay)
                    continue
                if "database is locked" in str(e):
                    logger.error("数据库锁定重试均失败 (%d 次)", max_retries)
                raise

            try:
                yield conn
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()
            return

    def _init_db(self) -> None:
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.executescript("""
                CREATE TABLE IF NOT EXISTS vault_mappings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    placeholder TEXT NOT NULL,
                    real_value TEXT NOT NULL,
                    data_type TEXT NOT NULL,
                    team_id TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE INDEX IF NOT EXISTS idx_session ON vault_mappings(session_id);
                CREATE INDEX IF NOT EXISTS idx_placeholder ON vault_mappings(placeholder);
                CREATE INDEX IF NOT EXISTS idx_vault_team_session ON vault_mappings(team_id, session_id);

                CREATE TABLE IF NOT EXISTS custom_keywords (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    keyword TEXT UNIQUE NOT NULL,
                    team_id TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    team_id TEXT DEFAULT 'default',
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
                    total_count INTEGER DEFAULT 0,
                    UNIQUE(date, team_id)
                );

                CREATE INDEX IF NOT EXISTS idx_stats_team_date ON stats(team_id, date);

                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    action TEXT NOT NULL,
                    detail_json TEXT,
                    prev_hash TEXT,
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

                CREATE TABLE IF NOT EXISTS custom_regex_rules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    pattern TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    enabled INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def _ensure_initialized(self) -> None:
        """Health check: verify the database is accessible and tables exist.
        Raises on failure so callers can catch and handle."""
        with self.get_conn() as conn:
            conn.execute("SELECT 1 FROM vault_mappings LIMIT 1")

    def _encrypt_value(self, value: str) -> str:
        """Encrypt *value* if vault encryption is active, otherwise return as-is."""
        crypto = get_vault_crypto()
        if crypto is None:
            return value
        return crypto.encrypt(value)

    def _try_decrypt_value(self, value: str) -> str:
        """Try to decrypt *value*; return plaintext on success, fall back to original."""
        crypto = get_vault_crypto()
        if crypto is None:
            return value
        decrypted = crypto.decrypt(value)
        return decrypted if decrypted is not None else value

    def check_integrity(self) -> bool:
        """运行 PRAGMA integrity_check 验证数据库完整性"""
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("PRAGMA integrity_check")
                result = cursor.fetchone()[0]
                if result == "ok":
                    logger.info("数据库完整性检查通过")
                    return True
                logger.error("数据库完整性检查失败: %s", result)
                return False
        except Exception as e:
            logger.error("数据库完整性检查异常: %s", e)
            return False

    def backup_vault(self, path: str) -> int:
        """备份 Vault 数据库到指定路径

        Args:
            path: 备份文件路径

        Returns:
            备份文件大小（字节）
        """
        dest_dir = os.path.dirname(path)
        if dest_dir:
            os.makedirs(dest_dir, exist_ok=True)
        with sqlite3.connect(path) as dest:
            src = sqlite3.connect(self.db_path)
            try:
                src.backup(dest, pages=1)
            finally:
                src.close()
        size = os.path.getsize(path)
        logger.info("Vault 备份完成: %s (%d 字节)", path, size)
        return size

    def restore_vault(self, path: str, force: bool = False) -> bool:
        """从备份文件恢复 Vault 数据库

        Args:
            path: 备份文件路径
            force: 如果为 True，允许覆盖非空 Vault

        Returns:
            恢复成功返回 True

        Raises:
            ValueError: Vault 非空且 force=False
            RuntimeError: 恢复后完整性检查失败
        """
        # 检查当前 Vault 是否为空
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vault_mappings")
            count = cursor.fetchone()[0]
            if count > 0 and not force:
                raise ValueError("保险库非空，如需覆盖请设置 force=True")

        # 执行恢复（从备份文件复制到主数据库）
        with sqlite3.connect(path) as src:
            dest = sqlite3.connect(self.db_path)
            try:
                dest.execute("PRAGMA journal_mode=WAL")
                src.backup(dest, pages=1)
            finally:
                dest.close()

        # 验证完整性
        if not self.check_integrity():
            raise RuntimeError("恢复后完整性检查失败")

        logger.info("从 %s 恢复 Vault 成功", path)
        return True

    def save_mappings(self, session_id: str, mappings: Dict[str, str], data_type: str = "unknown", team_id: Optional[str] = None) -> None:
        # Encrypt values if vault encryption is active
        encrypted = {k: self._encrypt_value(v) for k, v in mappings.items()}

        if app_config.STATELESS_MODE:
            # 无状态模式：仅存内存，不写 SQLite
            if session_id not in self._memory_mappings:
                self._memory_mappings[session_id] = {}
            self._memory_mappings[session_id].update(encrypted)
            self._memory_mapping_times[session_id] = datetime.utcnow()
            logger.info(f"[无状态] 保存 {len(encrypted)} 条映射记录到内存")
            return

        with self.get_conn() as conn:
            cursor = conn.cursor()
            for placeholder, real_value in encrypted.items():
                cursor.execute(
                    "INSERT INTO vault_mappings (session_id, placeholder, real_value, data_type, team_id) VALUES (?, ?, ?, ?, COALESCE(?, 'default'))",
                    (session_id, placeholder, real_value, data_type, team_id)
                )
        logger.info(f"保存 {len(encrypted)} 条映射记录")

    def cleanup_expired_mappings(self, retention_hours: Optional[int] = None) -> int:
        """清理超过保留时长的映射记录（使用 self.mapping_ttl 秒数）"""
        # 使用 self.mapping_ttl（秒）换算为小时作为默认值
        hours = retention_hours if retention_hours is not None else max(1, self.mapping_ttl // 3600)
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).strftime("%Y-%m-%d %H:%M:%S")

        # 清理过期内存映射
        if self._memory_mappings and self.mapping_ttl > 0:
            mem_cutoff = datetime.utcnow() - timedelta(seconds=self.mapping_ttl)
            expired_sessions = [
                sid for sid in self._memory_mappings
                if self._memory_mapping_times.get(sid, datetime.min) < mem_cutoff
            ]
            for sid in expired_sessions:
                self._memory_mappings.pop(sid, None)
                self._memory_mapping_times.pop(sid, None)
            if expired_sessions:
                logger.info(f"[内存] 清理了 {len(expired_sessions)} 条过期映射 (保留 {hours} 小时)")

        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM vault_mappings WHERE created_at < ?", (cutoff,))
            deleted = cursor.rowcount
        if deleted > 0:
            logger.info(f"清理了 {deleted} 条过期映射记录 (保留 {hours} 小时)")
        return deleted

    def get_all_mappings(self) -> Dict[str, str]:
        mappings = {}
        # 包含内存映射
        for session_mappings in self._memory_mappings.values():
            for placeholder, value in session_mappings.items():
                if placeholder not in mappings:
                    mappings[placeholder] = self._try_decrypt_value(value)
        # 同时包含 SQLite 中持久化的映射
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT placeholder, real_value FROM vault_mappings")
            for row in cursor.fetchall():
                if row["placeholder"] not in mappings:
                    mappings[row["placeholder"]] = self._try_decrypt_value(row["real_value"])
        return mappings

    def get_mapping(self, session_id: str, placeholder: str) -> Optional[str]:
        # 优先检查内存映射（无状态模式下 SQLite 没有映射数据）
        if session_id in self._memory_mappings and placeholder in self._memory_mappings[session_id]:
            return self._try_decrypt_value(self._memory_mappings[session_id][placeholder])

        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT real_value FROM vault_mappings WHERE session_id = ? AND placeholder = ?",
                (session_id, placeholder)
            )
            row = cursor.fetchone()
            return self._try_decrypt_value(row["real_value"]) if row else None

    def clear_session(self, session_id: str) -> None:
        # 清理内存映射
        self._memory_mappings.pop(session_id, None)
        self._memory_mapping_times.pop(session_id, None)
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

    # ==================== Custom Regex Rules ====================

    def add_custom_regex_rule(self, name: str, pattern: str, entity_type: str) -> int:
        """添加自定义正则规则，返回新规则ID，名称冲突时返回 -1"""
        try:
            with self.get_conn() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO custom_regex_rules (name, pattern, entity_type) VALUES (?, ?, ?)",
                    (name, pattern, entity_type)
                )
                return cursor.lastrowid or -1
        except sqlite3.IntegrityError:
            return -1

    def delete_custom_regex_rule(self, rule_id: int) -> bool:
        """删除自定义正则规则"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM custom_regex_rules WHERE id = ?", (rule_id,))
            return cursor.rowcount > 0

    def get_custom_regex_rules(self) -> List[Dict[str, Any]]:
        """获取所有自定义正则规则"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, pattern, entity_type, enabled, created_at "
                "FROM custom_regex_rules ORDER BY id ASC"
            )
            return [dict(row) for row in cursor.fetchall()]

    def toggle_custom_regex_rule(self, rule_id: int, enabled: bool) -> bool:
        """启用/禁用自定义正则规则"""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE custom_regex_rules SET enabled = ? WHERE id = ?",
                (1 if enabled else 0, rule_id)
            )
            return cursor.rowcount > 0

    def clear_all_mappings(self) -> None:
        self._memory_mappings.clear()
        self._memory_mapping_times.clear()
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

    def update_stats(self, stats: Dict[str, int], team_id: Optional[str] = "default") -> None:
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
                INSERT INTO stats (date, team_id, {', '.join([f"{f}_count" for f in old_fields + new_fields])}, total_count)
                VALUES (?, ?, {', '.join(['?'] * (len(old_fields + new_fields) + 1))})
                ON CONFLICT(date, team_id) DO UPDATE SET
                {', '.join(set_clauses)},
                total_count = total_count + ?
            """

            insert_values: List[Any] = [today, team_id or "default"]
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

    def get_stats_range(self, from_date: str, to_date: str) -> List[Dict[str, Any]]:
        """Get daily stats for a date range (inclusive).
        Returns list of row dicts sorted by date ascending."""
        with self.get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM stats WHERE date >= ? AND date <= ? ORDER BY date ASC",
                (from_date, to_date)
            )
            return [dict(row) for row in cursor.fetchall()]



db = Database()

