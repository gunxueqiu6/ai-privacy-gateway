use hmac::{Hmac, Mac};
use pyo3::prelude::*;
use sha2::Sha256;
use std::fmt::Write;

type HmacSha256 = Hmac<Sha256>;

const DEFAULT_SECRET: &str = "integrity-check-default-key";

/// Verify the integrity of the `mappings` table.
///
/// Computes the HMAC-SHA256 checksum of the current table contents and
/// compares it against the value previously stored in `_integrity`.
/// Returns `true` when they match (table has not been tampered with)
/// and `false` when they differ or no stored checksum exists.
#[pyfunction]
pub fn verify(db_path: String, secret: Option<String>) -> PyResult<bool> {
    let key = secret.unwrap_or_else(|| DEFAULT_SECRET.to_string());
    let conn = open_db(&db_path)?;
    let data = read_mappings(&conn)?;
    let current = compute_hmac(&data, &key);

    match read_stored_checksum(&conn) {
        Ok(stored) => Ok(stored == current),
        Err(_) => Ok(false),
    }
}

/// Compute and store the HMAC-SHA256 checksum of the `mappings` table.
///
/// The checksum is written into the `_integrity` metadata table (created
/// if it does not exist).  Returns the hex digest.
#[pyfunction]
pub fn compute_checksum(db_path: String, secret: Option<String>) -> PyResult<String> {
    let key = secret.unwrap_or_else(|| DEFAULT_SECRET.to_string());
    let conn = open_db(&db_path)?;
    let data = read_mappings(&conn)?;
    let checksum = compute_hmac(&data, &key);

    ensure_integrity_table(&conn)?;
    store_checksum(&conn, &checksum)?;

    Ok(checksum)
}

// ---------------------------------------------------------------------------
// PyO3 module registration
// ---------------------------------------------------------------------------

#[pymodule]
fn integrity_check(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(verify, m)?)?;
    m.add_function(wrap_pyfunction!(compute_checksum, m)?)?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

/// Open a read-write connection to the SQLite database at `path`.
fn open_db(path: &str) -> PyResult<rusqlite::Connection> {
    rusqlite::Connection::open(path).map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "failed to open database '{}': {}",
            path, e
        ))
    })
}

/// Read every row from `mappings`, sorted by `placeholder`.
/// Returns a single concatenated string: `placeholder1original1placeholder2original2...`
fn read_mappings(conn: &rusqlite::Connection) -> PyResult<String> {
    let mut stmt = conn
        .prepare("SELECT placeholder, original FROM mappings ORDER BY placeholder")
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "failed to prepare query: {}",
                e
            ))
        })?;

    let rows = stmt
        .query_map([], |row| {
            let placeholder: String = row.get(0)?;
            let original: String = row.get(1)?;
            Ok((placeholder, original))
        })
        .map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "failed to query mappings table: {}",
                e
            ))
        })?;

    let mut buf = String::new();
    for row in rows {
        let (placeholder, original) = row.map_err(|e| {
            pyo3::exceptions::PyRuntimeError::new_err(format!(
                "failed to read row: {}",
                e
            ))
        })?;
        buf.push_str(&placeholder);
        buf.push_str(&original);
    }
    Ok(buf)
}

/// Compute HMAC-SHA256 digest of `data` with `key`, returned as lowercase hex.
fn compute_hmac(data: &str, key: &str) -> String {
    let mut mac = HmacSha256::new_from_slice(key.as_bytes())
        .expect("HMAC accepts any key length");
    mac.update(data.as_bytes());
    let result = mac.finalize();
    let code_bytes = result.into_bytes();

    let mut hex = String::with_capacity(64);
    for b in &code_bytes {
        write!(hex, "{:02x}", b).unwrap();
    }
    hex
}

/// Ensure the `_integrity` table exists.
fn ensure_integrity_table(conn: &rusqlite::Connection) -> PyResult<()> {
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _integrity (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )",
        [],
    )
    .map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "failed to create _integrity table: {}",
            e
        ))
    })?;
    Ok(())
}

/// Read the stored checksum from the `_integrity` table.
fn read_stored_checksum(conn: &rusqlite::Connection) -> PyResult<String> {
    let result: Result<String, _> = conn.query_row(
        "SELECT value FROM _integrity WHERE key = 'mappings_checksum'",
        [],
        |row| row.get(0),
    );
    result.map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "failed to read stored checksum: {}",
            e
        ))
    })
}

/// Write (UPSERT) the checksum into the `_integrity` table.
fn store_checksum(conn: &rusqlite::Connection, checksum: &str) -> PyResult<()> {
    conn.execute(
        "INSERT INTO _integrity (key, value) VALUES ('mappings_checksum', ?1)
         ON CONFLICT(key) DO UPDATE SET value = ?1",
        [checksum],
    )
    .map_err(|e| {
        pyo3::exceptions::PyRuntimeError::new_err(format!(
            "failed to store checksum: {}",
            e
        ))
    })?;
    Ok(())
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn setup_db() -> rusqlite::Connection {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        conn.execute(
            "CREATE TABLE mappings (
                placeholder TEXT PRIMARY KEY,
                original TEXT NOT NULL
            )",
            [],
        )
        .unwrap();
        conn
    }

    fn seed_mappings(conn: &rusqlite::Connection, pairs: &[(&str, &str)]) {
        let mut stmt = conn
            .prepare("INSERT INTO mappings (placeholder, original) VALUES (?1, ?2)")
            .unwrap();
        for (ph, orig) in pairs {
            stmt.execute([ph, orig]).unwrap();
        }
    }

    // --- compute_hmac ---

    #[test]
    fn hmac_produces_consistent_output() {
        let a = compute_hmac("hello", "secret");
        let b = compute_hmac("hello", "secret");
        assert_eq!(a, b);
    }

    #[test]
    fn hmac_differs_on_different_data() {
        let a = compute_hmac("hello", "secret");
        let b = compute_hmac("world", "secret");
        assert_ne!(a, b);
    }

    #[test]
    fn hmac_differs_on_different_key() {
        let a = compute_hmac("hello", "key1");
        let b = compute_hmac("hello", "key2");
        assert_ne!(a, b);
    }

    #[test]
    fn hmac_output_is_64_char_hex() {
        let h = compute_hmac("test", "key");
        assert_eq!(h.len(), 64);
        assert!(h.chars().all(|c| c.is_ascii_hexdigit()));
    }

    // --- ensure_integrity_table ---

    #[test]
    fn ensure_integrity_table_creates_on_first_call() {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        ensure_integrity_table(&conn).unwrap();

        let count: i64 = conn
            .query_row(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='_integrity'",
                [],
                |r| r.get(0),
            )
            .unwrap();
        assert_eq!(count, 1);
    }

    #[test]
    fn ensure_integrity_table_is_idempotent() {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        ensure_integrity_table(&conn).unwrap();
        ensure_integrity_table(&conn).unwrap(); // 不应 panic
    }

    // --- store_checksum + read_stored_checksum ---

    #[test]
    fn store_and_read_roundtrip() {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        ensure_integrity_table(&conn).unwrap();
        store_checksum(&conn, "abcdef1234567890").unwrap();
        let stored = read_stored_checksum(&conn).unwrap();
        assert_eq!(stored, "abcdef1234567890");
    }

    #[test]
    fn store_overwrites_previous_checksum() {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        ensure_integrity_table(&conn).unwrap();
        store_checksum(&conn, "aaaa").unwrap();
        store_checksum(&conn, "bbbb").unwrap();
        assert_eq!(read_stored_checksum(&conn).unwrap(), "bbbb");
    }

    #[test]
    fn read_stored_checksum_fails_without_table() {
        let conn = rusqlite::Connection::open_in_memory().unwrap();
        let result = read_stored_checksum(&conn);
        assert!(result.is_err());
    }

    // --- read_mappings ---

    #[test]
    fn read_mappings_concatenates_placeholder_original_sorted() {
        let conn = setup_db();
        seed_mappings(&conn, &[("B", "b"), ("A", "a"), ("C", "c")]);

        let data = read_mappings(&conn).unwrap();
        // 按 placeholder 排序: A,a B,b C,c
        assert_eq!(data, "AaBbCc");
    }

    #[test]
    fn read_mappings_returns_empty_for_empty_table() {
        let conn = setup_db();
        let data = read_mappings(&conn).unwrap();
        assert!(data.is_empty());
    }

    #[test]
    fn read_mappings_handles_empty_strings() {
        let conn = setup_db();
        seed_mappings(&conn, &[("X", "")]);

        let data = read_mappings(&conn).unwrap();
        assert_eq!(data, "X");
    }

    // --- full-flow verify + compute_checksum (in-memory) ---

    #[test]
    fn full_flow_compute_then_verify() {
        let conn = setup_db();
        seed_mappings(&conn, &[("p1", "o1"), ("p2", "o2")]);

        let data = read_mappings(&conn).unwrap();
        let key = "test-secret";
        let checksum = compute_hmac(&data, key);

        ensure_integrity_table(&conn).unwrap();
        store_checksum(&conn, &checksum).unwrap();

        let data2 = read_mappings(&conn).unwrap();
        let current = compute_hmac(&data2, key);
        let stored = read_stored_checksum(&conn).unwrap();
        assert_eq!(stored, current);
    }

    #[test]
    fn detect_tampered_data() {
        let conn = setup_db();
        seed_mappings(&conn, &[("p1", "original")]);

        let key = "secret";
        let data = read_mappings(&conn).unwrap();
        let checksum = compute_hmac(&data, key);

        ensure_integrity_table(&conn).unwrap();
        store_checksum(&conn, &checksum).unwrap();

        // 篡改数据
        conn.execute(
            "UPDATE mappings SET original = 'hacked' WHERE placeholder = 'p1'",
            [],
        )
        .unwrap();

        let data2 = read_mappings(&conn).unwrap();
        let current = compute_hmac(&data2, key);
        let stored = read_stored_checksum(&conn).unwrap();
        assert_ne!(stored, current);
    }

    #[test]
    fn same_data_different_key_produces_different_checksum() {
        let conn = setup_db();
        seed_mappings(&conn, &[("p1", "o1")]);

        let data = read_mappings(&conn).unwrap();
        let h1 = compute_hmac(&data, "key-a");
        let h2 = compute_hmac(&data, "key-b");
        assert_ne!(h1, h2);
    }
}
