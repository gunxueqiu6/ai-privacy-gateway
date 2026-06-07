"""
License 持久化存储 — SQLite 替代内存字典
支持 license 的创建、查询、撤销、列表
"""
import os
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Optional

DB_PATH = os.environ.get("LICENSE_DB_PATH", "./license_data/licenses.db")


def _connect() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS licenses (
            license_key TEXT PRIMARY KEY,
            customer_email TEXT NOT NULL,
            tier TEXT NOT NULL CHECK(tier IN ('pro', 'enterprise')),
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'revoked', 'expired')),
            max_concurrent INTEGER NOT NULL DEFAULT 20,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            revoked_at TEXT,
            notes TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS hardware_bindings (
            license_key TEXT PRIMARY KEY REFERENCES licenses(license_key),
            board_serial TEXT DEFAULT '',
            disk_uuid TEXT DEFAULT '',
            mac_address TEXT DEFAULT '',
            container_id TEXT DEFAULT '',
            hostname TEXT DEFAULT '',
            bound_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS active_sessions (
            session_id TEXT PRIMARY KEY,
            license_key TEXT NOT NULL REFERENCES licenses(license_key),
            jwt_token TEXT NOT NULL,
            container_id TEXT DEFAULT '',
            last_heartbeat TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_licenses_status ON licenses(status);
        CREATE INDEX IF NOT EXISTS idx_licenses_email ON licenses(customer_email);
        CREATE INDEX IF NOT EXISTS idx_sessions_license ON active_sessions(license_key);
        CREATE INDEX IF NOT EXISTS idx_sessions_token ON active_sessions(jwt_token);
    """)
    conn.commit()
    conn.close()


def generate_key() -> str:
    """生成唯一的 License Key: PRIVGW-XXXX-XXXX-XXXX"""
    while True:
        seg = uuid.uuid4().hex.upper()
        key = f"PRIVGW-{seg[:4]}-{seg[4:8]}-{seg[8:12]}"
        if not _key_exists(key):
            return key


def _key_exists(key: str) -> bool:
    conn = _connect()
    row = conn.execute("SELECT 1 FROM licenses WHERE license_key = ?", (key,)).fetchone()
    conn.close()
    return row is not None


# --- License CRUD ---

def create_license(
    customer_email: str,
    tier: str = "pro",
    expires_in_days: int = 365,
    max_concurrent: int = 20,
    notes: str = ""
) -> dict:
    """创建新 license，返回完整记录"""
    conn = _connect()
    key = generate_key()
    now = datetime.utcnow().isoformat()
    expires = (datetime.utcnow() + timedelta(days=expires_in_days)).isoformat()

    conn.execute(
        """INSERT INTO licenses (license_key, customer_email, tier, status,
           max_concurrent, created_at, expires_at, notes)
           VALUES (?, ?, ?, 'active', ?, ?, ?, ?)""",
        (key, customer_email, tier, max_concurrent, now, expires, notes)
    )
    conn.commit()

    row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (key,)).fetchone()
    conn.close()
    return dict(row)


def get_license(license_key: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute("SELECT * FROM licenses WHERE license_key = ?", (license_key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_licenses(status: Optional[str] = None, tier: Optional[str] = None) -> list[dict]:
    conn = _connect()
    query = "SELECT * FROM licenses WHERE 1=1"
    params = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if tier:
        query += " AND tier = ?"
        params.append(tier)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def revoke_license(license_key: str) -> bool:
    conn = _connect()
    now = datetime.utcnow().isoformat()
    cur = conn.execute(
        """UPDATE licenses SET status = 'revoked', revoked_at = ?
           WHERE license_key = ? AND status = 'active'""",
        (now, license_key)
    )
    conn.commit()
    affected = cur.rowcount
    conn.close()
    return affected > 0


def check_expired():
    """将过期 license 标记为 expired"""
    conn = _connect()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE licenses SET status = 'expired' WHERE status = 'active' AND expires_at < ?",
        (now,)
    )
    conn.commit()
    conn.close()


# --- Hardware Binding ---

def bind_hardware(license_key: str, fingerprint: dict) -> bool:
    """记录或更新硬件绑定，首次自动绑定"""
    conn = _connect()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT INTO hardware_bindings (license_key, board_serial, disk_uuid,
           mac_address, container_id, hostname, bound_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(license_key) DO UPDATE SET
           board_serial = excluded.board_serial,
           disk_uuid = excluded.disk_uuid,
           mac_address = excluded.mac_address,
           container_id = excluded.container_id,
           hostname = excluded.hostname,
           bound_at = excluded.bound_at""",
        (license_key,
         fingerprint.get("board_serial", ""),
         fingerprint.get("disk_uuid", ""),
         fingerprint.get("mac_address", ""),
         fingerprint.get("container_id", ""),
         fingerprint.get("hostname", ""),
         now)
    )
    conn.commit()
    conn.close()
    return True


def get_hardware_binding(license_key: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute("SELECT * FROM hardware_bindings WHERE license_key = ?", (license_key,)).fetchone()
    conn.close()
    return dict(row) if row else None


def verify_hardware(license_key: str, fingerprint: dict) -> bool:
    """验证硬件指纹：至少匹配 4/5 个因子"""
    stored = get_hardware_binding(license_key)
    if stored is None:
        return True  # 首次激活，允许绑定

    fields = ["board_serial", "disk_uuid", "mac_address", "container_id", "hostname"]
    match_count = sum(1 for f in fields if stored.get(f) == fingerprint.get(f))
    return match_count >= 4


# --- Sessions ---

def create_session(license_key: str, jwt_token: str, container_id: str = "") -> str:
    session_id = f"session_{uuid.uuid4().hex[:8]}"
    conn = _connect()
    now = datetime.utcnow().isoformat()
    conn.execute(
        """INSERT INTO active_sessions (session_id, license_key, jwt_token,
           container_id, last_heartbeat, created_at) VALUES (?, ?, ?, ?, ?, ?)""",
        (session_id, license_key, jwt_token, container_id, now, now)
    )
    conn.commit()
    conn.close()
    return session_id


def find_session_by_token(jwt_token: str) -> Optional[dict]:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM active_sessions WHERE jwt_token = ?", (jwt_token,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def touch_session(jwt_token: str):
    conn = _connect()
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE active_sessions SET last_heartbeat = ? WHERE jwt_token = ?",
        (now, jwt_token)
    )
    conn.commit()
    conn.close()


# 初始化
init_db()
