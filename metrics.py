"""
Prometheus 指标模块 - 网关监控指标定义。
"""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST

# 请求计数 (by endpoint, method, status code)
request_count = Counter(
    "gateway_request_count",
    "Total request count by endpoint, method, and status code",
    ["endpoint", "method", "status_code"],
)

# 请求延迟直方图 (by endpoint)
request_latency_seconds = Histogram(
    "gateway_request_latency_seconds",
    "Request latency in seconds by endpoint",
    ["endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float("inf")),
)

# PII 检测计数 (by entity type)
pii_detected_total = Counter(
    "gateway_pii_detected_total",
    "Total number of PII entities detected by entity type",
    ["entity_type"],
)

# PII 脱敏计数 (by entity type)
pii_masked_total = Counter(
    "gateway_pii_masked_total",
    "Total number of PII entities masked by entity type",
    ["entity_type"],
)

# 网关错误计数 (by error type)
gateway_errors_total = Counter(
    "gateway_errors_total",
    "Total number of gateway errors by error type",
    ["error_type"],
)

# 上游健康状态 (per upstream URL)
upstream_health_status = Gauge(
    "gateway_upstream_health_status",
    "Health status of upstream LLM endpoints (1=healthy, 0=unhealthy)",
    ["upstream_url"],
)
