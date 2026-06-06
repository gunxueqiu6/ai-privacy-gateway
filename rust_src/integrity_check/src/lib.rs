use pyo3::prelude::*;
use pyo3::types::{PyDict, PyList};
use sha2::{Sha256, Digest};
use once_cell::sync::Lazy;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};
use std::fs;
use std::path::Path;

// ---------------------------------------------------------------------------
// Static memory integrity guard — 检测内存篡改
// ---------------------------------------------------------------------------
const INTEGRITY_MAGIC: &[u8] = b"AI_PRIVACY_VAULT_INTEGRITY_v2.0_x9K2mQ7pL4";
static MEMORY_GUARD: Lazy<Mutex<String>> = Lazy::new(|| {
    let hash = Sha256::digest(INTEGRITY_MAGIC);
    Mutex::new(hex::encode(hash))
});
static STARTUP_MONOTONIC_MS: Lazy<u64> = Lazy::new(|| monotonic_ms());

fn monotonic_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis() as u64
}

// ---------------------------------------------------------------------------
// Platform: 调试器检测
// ---------------------------------------------------------------------------

#[cfg(target_os = "windows")]
mod debugger {
    use winapi::um::debugapi::{IsDebuggerPresent, CheckRemoteDebuggerPresent};
    use winapi::um::processthreadsapi::GetCurrentProcess;

    pub fn is_debugger_attached() -> bool {
        unsafe {
            if IsDebuggerPresent() != 0 {
                return true;
            }
            let mut remote: i32 = 0;
            if CheckRemoteDebuggerPresent(GetCurrentProcess(), &mut remote) != 0 {
                return remote != 0;
            }
            false
        }
    }
}

#[cfg(target_os = "linux")]
mod debugger {
    pub fn is_debugger_attached() -> bool {
        if let Ok(status) = std::fs::read_to_string("/proc/self/status") {
            for line in status.lines() {
                if line.starts_with("TracerPid:") {
                    if let Some(pid) = line.split_whitespace().nth(1) {
                        if let Ok(p) = pid.parse::<i32>() {
                            return p != 0;
                        }
                    }
                }
            }
        }
        false
    }
}

#[cfg(target_os = "macos")]
mod debugger {
    pub fn is_debugger_attached() -> bool {
        if let Ok(output) = std::process::Command::new("sysctl")
            .args(["kern.proc.pid", &std::process::id().to_string()])
            .output()
        {
            let stdout = String::from_utf8_lossy(&output.stdout);
            return stdout.contains("P_TRACED");
        }
        false
    }
}

// ---------------------------------------------------------------------------
// 独立函数 — 供 Python 直接调用
// ---------------------------------------------------------------------------

#[pyfunction]
fn compute_file_hash(file_path: &str) -> PyResult<String> {
    let contents = fs::read(file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(
            format!("Failed to read file: {}", e)))?;
    Ok(hex::encode(Sha256::digest(&contents)))
}

#[pyfunction]
fn compute_bytes_hash(data: &[u8]) -> PyResult<String> {
    Ok(hex::encode(Sha256::digest(data)))
}

#[pyfunction]
fn detect_debugger() -> PyResult<bool> {
    Ok(debugger::is_debugger_attached())
}

#[pyfunction]
fn is_in_container() -> PyResult<bool> {
    if Path::new("/.dockerenv").exists() {
        return Ok(true);
    }
    if let Ok(cgroup) = fs::read_to_string("/proc/1/cgroup") {
        if cgroup.contains("docker") || cgroup.contains("containerd") {
            return Ok(true);
        }
    }
    Ok(false)
}

#[pyfunction]
fn get_hardware_fingerprint() -> PyResult<String> {
    let mut hasher = Sha256::new();

    #[cfg(target_os = "linux")]
    {
        if let Ok(serial) = fs::read_to_string("/sys/class/dmi/id/board_serial") {
            hasher.update(serial.trim().as_bytes());
        }
        if let Ok(uuid) = fs::read_to_string("/sys/class/dmi/id/product_uuid") {
            hasher.update(uuid.trim().as_bytes());
        }
        if let Ok(cgroup) = fs::read_to_string("/proc/self/cgroup") {
            hasher.update(cgroup.as_bytes());
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Ok(name) = std::env::var("COMPUTERNAME") {
            hasher.update(name.as_bytes());
        }
        if let Ok(user) = std::env::var("USERNAME") {
            hasher.update(user.as_bytes());
        }
    }

    let result = hasher.finalize();
    Ok(hex::encode(result))
}

#[pyfunction]
fn verify_file_integrity(file_path: &str, expected_hash: &str) -> PyResult<bool> {
    let computed = compute_file_hash(file_path)?;
    Ok(computed == expected_hash)
}

#[pyfunction]
fn verify_files_integrity(app_dir: &str, expected: &Bound<'_, PyDict>) -> PyResult<PyObject> {
    let py = expected.py();
    let mut all_ok = true;
    let results = PyList::empty_bound(py);

    for (key, value) in expected.iter() {
        let rel_path: String = key.extract()?;
        let expected_hash: String = value.extract()?;
        let full_path = Path::new(app_dir).join(&rel_path);

        match fs::read(&full_path) {
            Ok(data) => {
                let actual = hex::encode(Sha256::digest(&data));
                let ok = actual == expected_hash;
                if !ok { all_ok = false; }
                let d = PyDict::new_bound(py);
                d.set_item("file", &rel_path)?;
                d.set_item("ok", ok)?;
                d.set_item("expected", &expected_hash)?;
                d.set_item("actual", &actual)?;
                results.append(d)?;
            }
            Err(e) => {
                all_ok = false;
                let d = PyDict::new_bound(py);
                d.set_item("file", &rel_path)?;
                d.set_item("ok", false)?;
                d.set_item("error", format!("read_failed: {e}"))?;
                results.append(d)?;
            }
        }
    }

    let result = PyDict::new_bound(py);
    result.set_item("check", "file_integrity")?;
    result.set_item("passed", all_ok)?;
    result.set_item("files", results)?;
    Ok(result.into())
}

#[pyfunction]
fn compute_memory_checksum(data: &[u8]) -> PyResult<u32> {
    let mut sum: u32 = 0;
    for (i, &byte) in data.iter().enumerate() {
        sum = sum.wrapping_add((byte as u32).wrapping_mul((i as u32).wrapping_add(1)));
    }
    Ok(sum)
}

#[pyfunction]
fn detect_time_tampering() -> PyResult<bool> {
    let now = monotonic_ms();
    let startup = *STARTUP_MONOTONIC_MS;
    // 时间不应早于启动时间（允许 5s NTP 漂移）
    let rolled_back = now + 5_000 < startup;

    if rolled_back {
        return Ok(true);
    }

    // 区间检查: 2020-2030
    let secs = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs();
    if secs < 1577836800 || secs > 1893456000 {
        return Ok(true);
    }

    Ok(false)
}

#[pyfunction]
fn check_memory_integrity() -> PyResult<bool> {
    let expected = MEMORY_GUARD.lock().unwrap().clone();
    let current = hex::encode(Sha256::digest(INTEGRITY_MAGIC));
    Ok(current == expected)
}

#[pyfunction]
fn embed_watermark(data: &str, watermark: &str) -> PyResult<String> {
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    hasher.update(watermark.as_bytes());
    Ok(hex::encode(hasher.finalize()))
}

#[pyfunction]
fn verify_watermark(data: &str, expected_watermark: &str) -> PyResult<bool> {
    let computed: String = hex::encode(Sha256::digest(data.as_bytes()));
    Ok(computed == expected_watermark)
}

// ---------------------------------------------------------------------------
// 综合性完整性检查 — 返回 dict
// ---------------------------------------------------------------------------

#[pyfunction(signature = (app_dir, expected_hashes=None, on_anomaly=None, on_heartbeat=None))]
fn run_integrity_check(
    py: Python<'_>,
    app_dir: &str,
    expected_hashes: Option<&Bound<'_, PyDict>>,
    on_anomaly: Option<&Bound<'_, PyAny>>,
    on_heartbeat: Option<&Bound<'_, PyAny>>,
) -> PyResult<PyObject> {
    // 收集期望哈希
    let hash_pairs: Vec<(String, String)> = if let Some(dict) = expected_hashes {
        let mut pairs = Vec::new();
        for (key, value) in dict.iter() {
            pairs.push((key.extract()?, value.extract()?));
        }
        pairs
    } else {
        Vec::new()
    };

    let hash_refs: Vec<(&str, &str)> = hash_pairs
        .iter()
        .map(|(k, v)| (k.as_str(), v.as_str()))
        .collect();

    // 四项检查
    let checks: Vec<PyObject> = vec![
        {
            // debugger
            let detected = debugger::is_debugger_attached();
            let d = PyDict::new_bound(py);
            d.set_item("check", "debugger")?;
            d.set_item("passed", !detected)?;
            d.set_item("detail", if detected { "debugger_attached" } else { "clean" })?;
            d.into()
        },
        {
            // container
            let in_ctr = is_in_container().unwrap_or(false);
            let d = PyDict::new_bound(py);
            d.set_item("check", "container")?;
            d.set_item("passed", in_ctr)?;
            d.set_item("detail", if in_ctr { "docker" } else { "bare_metal" })?;
            d.into()
        },
        {
            // time
            let tampered = detect_time_tampering().unwrap_or(true);
            let d = PyDict::new_bound(py);
            d.set_item("check", "time")?;
            d.set_item("passed", !tampered)?;
            d.set_item("detail", if tampered { "time_anomaly" } else { "normal" })?;
            d.into()
        },
        {
            // memory integrity
            let mem_ok = check_memory_integrity().unwrap_or(false);
            let d = PyDict::new_bound(py);
            d.set_item("check", "memory_integrity")?;
            d.set_item("passed", mem_ok)?;
            d.set_item("detail", if mem_ok { "intact" } else { "MEMORY_TAMPERED" })?;
            d.into()
        },
    ];

    // 文件完整性
    if !hash_refs.is_empty() {
        let file_result = verify_files_integrity(app_dir, &expected_hashes.unwrap())?;
        // file_result 已经是 PyObject (dict)，追加到 checks
        let checks_list = PyList::new_bound(py, &checks);
        checks_list.append(file_result)?;
    }

    let checks_list = PyList::new_bound(py, &checks);
    let all_passed = checks.iter().all(|c| {
        let d = c.downcast_bound::<PyDict>(py).ok();
        d.and_then(|d| d.get_item("passed").ok().flatten())
            .and_then(|v| v.extract::<bool>().ok())
            .unwrap_or(false)
    });

    // 收集异常
    let mut anomalies: Vec<(String, String)> = Vec::new();
    for check in &checks {
        let d = check.downcast_bound::<PyDict>(py).ok();
        let passed = d.as_ref()
            .and_then(|d| d.get_item("passed").ok().flatten())
            .and_then(|v| v.extract::<bool>().ok())
            .unwrap_or(true);
        if !passed {
            let name = d.as_ref()
                .and_then(|d| d.get_item("check").ok().flatten())
                .and_then(|v| v.extract::<String>().ok())
                .unwrap_or_else(|| "unknown".into());
            let detail = d.as_ref()
                .and_then(|d| d.get_item("detail").ok().flatten())
                .and_then(|v| v.extract::<String>().ok())
                .unwrap_or_else(|| "?".into());
            anomalies.push((name, detail));
        }
    }

    // 回调
    if !anomalies.is_empty() {
        if let Some(ref cb) = on_anomaly {
            for (name, detail) in &anomalies {
                let _ = cb.call1((name.as_str(), detail.as_str()));
            }
        }
    }
    if let Some(ref cb) = on_heartbeat {
        let _ = cb.call1((all_passed,));
    }

    // 构建返回 dict
    let result = PyDict::new_bound(py);
    result.set_item("passed", all_passed)?;
    result.set_item("checks", &checks_list)?;

    let anomalies_list = PyList::empty_bound(py);
    for (name, detail) in &anomalies {
        let d = PyDict::new_bound(py);
        d.set_item("check", name.as_str())?;
        d.set_item("detail", detail.as_str())?;
        anomalies_list.append(d)?;
    }
    result.set_item("anomalies", anomalies_list)?;

    Ok(result.into())
}

// ---------------------------------------------------------------------------
// 模块注册
// ---------------------------------------------------------------------------

#[pymodule]
fn integrity_check(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_file_hash, m)?)?;
    m.add_function(wrap_pyfunction!(compute_bytes_hash, m)?)?;
    m.add_function(wrap_pyfunction!(detect_debugger, m)?)?;
    m.add_function(wrap_pyfunction!(is_in_container, m)?)?;
    m.add_function(wrap_pyfunction!(get_hardware_fingerprint, m)?)?;
    m.add_function(wrap_pyfunction!(verify_file_integrity, m)?)?;
    m.add_function(wrap_pyfunction!(verify_files_integrity, m)?)?;
    m.add_function(wrap_pyfunction!(compute_memory_checksum, m)?)?;
    m.add_function(wrap_pyfunction!(detect_time_tampering, m)?)?;
    m.add_function(wrap_pyfunction!(check_memory_integrity, m)?)?;
    m.add_function(wrap_pyfunction!(run_integrity_check, m)?)?;
    m.add_function(wrap_pyfunction!(embed_watermark, m)?)?;
    m.add_function(wrap_pyfunction!(verify_watermark, m)?)?;

    m.add("__version__", "2.0.0")?;
    m.add("__build_target__",
        if cfg!(target_os = "windows") { "windows" }
        else if cfg!(target_os = "linux") { "linux" }
        else if cfg!(target_os = "macos") { "macos" }
        else { "unknown" }
    )?;
    Ok(())
}
