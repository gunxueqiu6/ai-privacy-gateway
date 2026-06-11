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
