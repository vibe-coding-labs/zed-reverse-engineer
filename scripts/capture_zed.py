"""
Zed 网络流量抓包脚本 (mitmproxy)
===================================
使用方法:
  1. 启动 mitmproxy:
     mitmdump -s scripts/capture_zed.py

  2. 启动 Zed (通过代理):
     https_proxy=http://127.0.0.1:8080 zed &
     # 或者:
     export HTTP_PROXY=http://127.0.0.1:8080
     export HTTPS_PROXY=http://127.0.0.1:8080
     zed

  3. 正常使用 Zed（登录、聊天等）

  4. 查看捕获结果:
     mitmproxy 会打印所有匹配的请求到终端
     同时保存到 /tmp/zed_capture_*.txt
"""

import json
import os
from datetime import datetime
from mitmproxy import http

# 只捕获这些域名的流量
TARGET_DOMAINS = [
    "cloud.zed.dev",
    "zed.dev",
    "llm-staging.zed.dev",
    "api.anthropic.com",
]

# 输出文件
OUTPUT_DIR = "/tmp"
capture_file = None


def request(flow: http.HTTPFlow) -> None:
    """捕获请求"""
    host = flow.request.pretty_host

    if host not in TARGET_DOMAINS and not host.endswith(".zed.dev"):
        return

    # 脱敏处理
    sanitized_headers = dict(flow.request.headers)
    if "authorization" in sanitized_headers:
        val = sanitized_headers["authorization"]
        if len(val) > 20:
            sanitized_headers["authorization"] = val[:15] + "..." + val[-5:]
    if "x-api-key" in sanitized_headers:
        val = sanitized_headers["x-api-key"]
        if len(val) > 10:
            sanitized_headers["x-api-key"] = val[:8] + "..."

    # 构建日志
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "method": flow.request.method,
        "url": flow.request.pretty_url,
        "host": host,
        "headers": dict(sanitized_headers),
    }

    # 尝试解析请求体
    if flow.request.content:
        content_type = flow.request.headers.get("content-type", "")
        if "json" in content_type:
            try:
                log_entry["body"] = json.loads(flow.request.content)
            except json.JSONDecodeError:
                log_entry["body"] = flow.request.content[:500].decode("utf-8", errors="replace")
        elif flow.request.content and len(flow.request.content) < 10000:
            log_entry["body"] = flow.request.content[:1000].decode("utf-8", errors="replace")

    # 打印
    print(f"\n{'='*60}")
    print(f"⬆️  {flow.request.method} {flow.request.pretty_url}")
    print(f"   授权头: {sanitized_headers.get('authorization', 'N/A')}")

    if "body" in log_entry:
        body_str = json.dumps(log_entry["body"], indent=2, ensure_ascii=False)
        if len(body_str) > 2000:
            body_str = body_str[:2000] + "\n  ... (truncated)"
        print(f"   请求体: {body_str}")

    # 写入文件
    write_capture(log_entry)


def response(flow: http.HTTPFlow) -> None:
    """捕获响应"""
    host = flow.request.pretty_host

    if host not in TARGET_DOMAINS and not host.endswith(".zed.dev"):
        return

    status = flow.response.status_code
    content_type = flow.response.headers.get("content-type", "")
    content_length = len(flow.response.content) if flow.response.content else 0

    print(f"⬇️  {status} {flow.request.method} {flow.request.pretty_url}")
    print(f"   Content-Type: {content_type}, Size: {content_length} bytes")
    print(f"   响应头: dict(", end="")

    # 打印关键响应头
    interesting_headers = [
        "x-zed-expired-token", "x-zed-outdated-token",
        "x-zed-edit-predictions-usage-limit", "x-zed-edit-predictions-usage-amount",
        "x-zed-minimum-required-version", "x-zed-server-supports-status-messages",
    ]
    for h in interesting_headers:
        if h in flow.response.headers:
            val = flow.response.headers[h]
            print(f"{h}={val}", end=", ")
    print(")")

    # 对 JSON 响应打印前几行
    if "json" in content_type and flow.response.content:
        try:
            data = json.loads(flow.response.content)
            body_str = json.dumps(data, indent=2, ensure_ascii=False)
            if len(body_str) > 3000:
                body_str = body_str[:3000] + "\n  ... (truncated)"
            print(f"   响应体: {body_str}")
        except json.JSONDecodeError:
            pass

    # 保存响应到文件
    write_capture({
        "timestamp": datetime.now().isoformat(),
        "type": "response",
        "url": flow.request.pretty_url,
        "status": status,
        "headers": dict(flow.response.headers),
        "body_length": content_length,
    })


def write_capture(data: dict):
    """将捕获数据写入文件"""
    global capture_file
    if capture_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        capture_file = os.path.join(OUTPUT_DIR, f"zed_capture_{timestamp}.txt")

    with open(capture_file, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")


def done():
    """退出时打印总结"""
    global capture_file
    if capture_file and os.path.exists(capture_file):
        print(f"\n\n捕获数据已保存到: {capture_file}")
        print("可以用以下命令查看:")
        print(f"  cat {capture_file} | python -m json.tool")