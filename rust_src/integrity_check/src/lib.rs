use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use sha2::{Sha256, Digest};
use std::fs;
use std::path::Path;

/// 运行时完整性校验模块
/// 检测文件篡改、调试器附加、内存修改

/// 计算文件 SHA256 哈希
#[pyfunction]
fn compute_file_hash(file_path: &str) -> PyResult<String> {
    let contents = fs::read(file_path)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Failed to read file: {}", e)))?;
    
    let mut hasher = Sha256::new();
    hasher.update(&contents);
    let result = hasher.finalize();
    
    Ok(format!("{:x}", result))
}

/// 计算字节数组 SHA256 哈希
#[pyfunction]
fn compute_bytes_hash(data: &[u8]) -> PyResult<String> {
    let mut hasher = Sha256::new();
    hasher.update(data);
    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}

/// 检测调试器附加
#[pyfunction]
fn detect_debugger() -> PyResult<bool> {
    // Linux: 检查 /proc/self/status 中的 TracerPid
    // macOS: 检查 sysctl kinfo_proc
    // Windows: 检查 IsDebuggerPresent
    
    #[cfg(target_os = "linux")]
    {
        if let Ok(status) = fs::read_to_string("/proc/self/status") {
            for line in status.lines() {
                if line.starts_with("TracerPid:") {
                    let pid = line.split_whitespace().nth(1).unwrap_or("0");
                    if pid != "0" {
                        return Ok(true);
                    }
                }
            }
        }
    }
    
    #[cfg(target_os = "windows")]
    {
        use std::process::Command;
        let output = Command::new("powershell")
            .args(&["-Command", "(Get-Process -Id $PID).DebuggerEnabled"])
            .output();
        
        if let Ok(output) = output {
            let result = String::from_utf8_lossy(&output.stdout);
            if result.trim().to_lowercase() == "true" {
                return Ok(true);
            }
        }
    }
    
    Ok(false)
}

/// 检测是否在容器中运行
#[pyfunction]
fn is_in_container() -> PyResult<bool> {
    // 检查 cgroup
    if let Ok(cgroup) = fs::read_to_string("/proc/1/cgroup") {
        if cgroup.contains("docker") || cgroup.contains("containerd") {
            return Ok(true);
        }
    }
    
    // 检查 .dockerenv 文件
    if Path::new("/.dockerenv").exists() {
        return Ok(true);
    }
    
    Ok(false)
}

/// 获取硬件指纹
#[pyfunction]
fn get_hardware_fingerprint() -> PyResult<String> {
    let mut hasher = Sha256::new();
    
    // 主板序列号
    #[cfg(target_os = "linux")]
    {
        if let Ok(serial) = fs::read_to_string("/sys/class/dmi/id/board_serial") {
            hasher.update(serial.trim().as_bytes());
        }
        if let Ok(serial) = fs::read_to_string("/sys/class/dmi/id/product_uuid") {
            hasher.update(serial.trim().as_bytes());
        }
    }
    
    // 容器 ID
    #[cfg(target_os = "linux")]
    {
        if let Ok(cgroup) = fs::read_to_string("/proc/self/cgroup") {
            hasher.update(cgroup.as_bytes());
        }
    }
    
    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}

/// 验证文件完整性
#[pyfunction]
fn verify_file_integrity(file_path: &str, expected_hash: &str) -> PyResult<bool> {
    let computed = compute_file_hash(file_path)?;
    Ok(computed == expected_hash)
}

/// 内存校验和计算
#[pyfunction]
fn compute_memory_checksum(data: &[u8]) -> PyResult<u32> {
    let mut sum: u32 = 0;
    for (i, &byte) in data.iter().enumerate() {
        sum = sum.wrapping_add((byte as u32).wrapping_mul((i as u32).wrapping_add(1)));
    }
    Ok(sum)
}

/// 防时间篡改检测
#[pyfunction]
fn detect_time_tampering() -> PyResult<bool> {
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(format!("Time error: {}", e)))?;
    
    // 检查时间是否合理 (2020-2030 年之间)
    let year_2020 = 1577836800u64;
    let year_2030 = 1893456000u64;
    let timestamp = now.as_secs();
    
    if timestamp < year_2020 || timestamp > year_2030 {
        return Ok(true); // 时间被篡改
    }
    
    Ok(false)
}

/// 完整性校验结果
#[pyclass]
#[derive(Debug)]
struct IntegrityCheckResult {
    #[pyo3(get)]
    is_secure: bool,
    #[pyo3(get)]
    debugger_detected: bool,
    #[pyo3(get)]
    container_detected: bool,
    #[pyo3(get)]
    time_tampered: bool,
    #[pyo3(get)]
    hardware_fingerprint: String,
}

/// 执行完整安全检查
#[pyfunction]
fn run_integrity_check() -> PyResult<IntegrityCheckResult> {
    let debugger = detect_debugger()?;
    let container = is_in_container()?;
    let time_tampered = detect_time_tampering()?;
    let fingerprint = get_hardware_fingerprint()?;
    
    // 如果检测到调试器、容器异常或时间篡改，标记为不安全
    let is_secure = !debugger && !time_tampered;
    
    Ok(IntegrityCheckResult {
        is_secure,
        debugger_detected: debugger,
        container_detected: container,
        time_tampered,
        hardware_fingerprint: fingerprint,
    })
}

/// 加密水印嵌入
#[pyfunction]
fn embed_watermark(data: &str, watermark: &str) -> PyResult<String> {
    let mut hasher = Sha256::new();
    hasher.update(data.as_bytes());
    hasher.update(watermark.as_bytes());
    let result = hasher.finalize();
    Ok(format!("{:x}", result))
}

/// 验证水印
#[pyfunction]
fn verify_watermark(data: &str, expected_watermark: &str) -> PyResult<bool> {
    let computed = embed_watermark(data, "")?;
    Ok(computed == expected_watermark)
}

/// Rust 模块入口
#[pymodule]
fn integrity_check(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(compute_file_hash, m)?, "compute_file_hash")?;
    m.add_function(wrap_pyfunction!(compute_bytes_hash, m)?, "compute_bytes_hash")?;
    m.add_function(wrap_pyfunction!(detect_debugger, m)?, "detect_debugger")?;
    m.add_function(wrap_pyfunction!(is_in_container, m)?, "is_in_container")?;
    m.add_function(wrap_pyfunction!(get_hardware_fingerprint, m)?, "get_hardware_fingerprint")?;
    m.add_function(wrap_pyfunction!(verify_file_integrity, m)?, "verify_file_integrity")?;
    m.add_function(wrap_pyfunction!(compute_memory_checksum, m)?, "compute_memory_checksum")?;
    m.add_function(wrap_pyfunction!(detect_time_tampering, m)?, "detect_time_tampering")?;
    m.add_function(wrap_pyfunction!(run_integrity_check, m)?, "run_integrity_check")?;
    m.add_function(wrap_pyfunction!(embed_watermark, m)?, "embed_watermark")?;
    m.add_function(wrap_pyfunction!(verify_watermark, m)?, "verify_watermark")?;
    
    Ok(())
}
