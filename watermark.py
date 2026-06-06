"""
水印注入脚本 - 为每个用户交付物嵌入唯一标识
泄露后可追溯源头
"""
import hashlib
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List


class WatermarkInjector:
    """水印注入器"""

    # 水印注入位置（分散在多处）
    INJECTION_POINTS = [
        # 文件头部注释
        {"file": "config.py", "position": "header", "format": "# _WM_H_: {watermark}"},
        # 函数内部隐藏变量
        {"file": "gateway_core.py", "position": "function", "format": "_wm_f = '{watermark}'"},
        # 类属性隐藏
        {"file": "mask_engine.py", "position": "class", "format": "_WM_ATTR = '{watermark}'"},
        # 字典隐藏键
        {"file": "database.py", "position": "dict", "format": "'_wm_k': '{watermark}'"},
        # 字符串拼接隐藏
        {"file": "stream_buffer.py", "position": "string", "format": "_wm_s = '{watermark}'"},
    ]

    def __init__(self, customer_id: str, license_key: str):
        self.customer_id = customer_id
        self.license_key = license_key
        self.watermark_id = self._generate_watermark_id()

    def _generate_watermark_id(self) -> str:
        """生成唯一水印ID"""
        data = {
            "customer_id": self.customer_id,
            "license_key": self.license_key,
            "timestamp": int(time.time()),
            "uuid": str(uuid.uuid4())
        }
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:32]

    def _encrypt_watermark(self) -> str:
        """加密水印（简单混淆）"""
        # 实际应使用 AES 加密
        raw = f"{self.watermark_id}:{self.customer_id}:{int(time.time())}"
        encoded = ''.join([chr(ord(c) + 3) for c in raw])  # 简单位移加密
        return encoded

    def inject(self, source_dir: str) -> Dict[str, str]:
        """
        注入水印到所有源文件
        返回注入记录
        """
        injection_records = {}

        for point in self.INJECTION_POINTS:
            file_path = Path(source_dir) / point["file"]

            if not file_path.exists():
                print(f"[SKIP] {point['file']} not found")
                continue

            watermark = self._encrypt_watermark()
            watermark_str = point["format"].format(watermark=watermark)

            with open(file_path, 'r') as f:
                content = f.read()

            # 检查是否已注入
            if watermark_str in content:
                print(f"[SKIP] {point['file']} already watermarked")
                continue

            # 根据位置注入
            if point["position"] == "header":
                # 文件头部
                new_content = watermark_str + "\n" + content
            elif point["position"] == "function":
                # 在某个函数内注入
                # 找到第一个函数定义
                lines = content.split('\n')
                injected = False
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if line.startswith('def ') and not injected:
                        new_lines.append(f"    {watermark_str}")
                        injected = True
                new_content = '\n'.join(new_lines)
            elif point["position"] == "class":
                # 在类定义内注入
                lines = content.split('\n')
                injected = False
                new_lines = []
                for line in lines:
                    new_lines.append(line)
                    if line.startswith('class ') and not injected:
                        new_lines.append(f"    {watermark_str}")
                        injected = True
                new_content = '\n'.join(new_lines)
            else:
                # 其他位置，在文件末尾注入
                new_content = content + "\n" + watermark_str + "\n"

            with open(file_path, 'w') as f:
                f.write(new_content)

            injection_records[point["file"]] = {
                "position": point["position"],
                "watermark_id": self.watermark_id,
                "injected_at": datetime.now().isoformat()
            }

            print(f"[INJECT] {point['file']} -> {point['position']}")

        return injection_records

    def generate_report(self) -> Dict:
        """生成水印报告"""
        return {
            "watermark_id": self.watermark_id,
            "customer_id": self.customer_id,
            "license_key": self.license_key[:8] + "...",
            "generated_at": datetime.now().isoformat(),
            "injection_points": len(self.INJECTION_POINTS)
        }


def extract_watermark(file_path: str) -> List[str]:
    """
    从文件中提取水印
    用于追溯泄露源
    """
    watermarks = []

    with open(file_path, 'r') as f:
        content = f.read()

    # 搜索水印模式
    patterns = [
        "# _WM_H_: ",
        "_wm_f = '",
        "_WM_ATTR = '",
        "'_wm_k': '",
        "_wm_s = '"
    ]

    for pattern in patterns:
        if pattern in content:
            # 提取水印值
            start = content.find(pattern) + len(pattern)
            end = content.find("'", start) if "'" in content[start:] else start + 50
            watermark = content[start:end]
            watermarks.append(watermark)

    return watermarks


def decrypt_watermark(encrypted: str) -> str:
    """解密水印"""
    # 简单位移解密
    decrypted = ''.join([chr(ord(c) - 3) for c in encrypted])
    return decrypted


def trace_leak(watermark_data: str) -> Dict:
    """
    追溯泄露源
    """
    try:
        decrypted = decrypt_watermark(watermark_data)
        parts = decrypted.split(':')

        return {
            "watermark_id": parts[0] if len(parts) > 0 else "unknown",
            "customer_id": parts[1] if len(parts) > 1 else "unknown",
            "timestamp": parts[2] if len(parts) > 2 else "unknown",
            "status": "traced"
        }
    except:
        return {
            "status": "invalid_watermark",
            "raw": watermark_data
        }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Watermark Injection Tool")
    parser.add_argument("--inject", action="store_true", help="Inject watermark")
    parser.add_argument("--extract", action="store_true", help="Extract watermark")
    parser.add_argument("--trace", type=str, help="Trace leak source")
    parser.add_argument("--customer-id", type=str, help="Customer ID")
    parser.add_argument("--license-key", type=str, help="License Key")
    parser.add_argument("--source-dir", type=str, default=".", help="Source directory")
    parser.add_argument("--file", type=str, help="File to extract from")

    args = parser.parse_args()

    if args.inject:
        if not args.customer_id or not args.license_key:
            print("Error: --customer-id and --license-key required for injection")
            exit(1)

        injector = WatermarkInjector(args.customer_id, args.license_key)
        records = injector.inject(args.source_dir)
        report = injector.generate_report()

        print("\nWatermark Report:")
        print(json.dumps(report, indent=2))

        # 保存报告
        report_file = f"watermark_report_{args.customer_id}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\nReport saved: {report_file}")

    elif args.extract:
        if not args.file:
            print("Error: --file required for extraction")
            exit(1)

        watermarks = extract_watermark(args.file)
        print(f"Extracted watermarks from {args.file}:")
        for wm in watermarks:
            print(f"  - {wm}")
            traced = trace_leak(wm)
            print(f"    Traced: {json.dumps(traced, indent=4)}")

    elif args.trace:
        traced = trace_leak(args.trace)
        print("Trace Result:")
        print(json.dumps(traced, indent=2))