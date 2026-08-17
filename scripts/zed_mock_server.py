#!/usr/bin/env python3
"""
Zed Cloud API Mock Server
==========================
模拟 cloud.zed.dev 的全部 API，用于验证协议分析和本地测试。

启动方式:
  python3 scripts/zed_mock_server.py --port 3000 --plan zed_pro --xvfb

然后在另一个终端:
  ZED_DEVELOPMENT_USE_KEYCHAIN=true ZED_SERVER_URL=http://localhost:3000 ./zed.app/libexec/zed-editor
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from typing import Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zed_auth import generate_keypair, serialize_public_key, random_token, token_fingerprint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zed_mock")

# ============================================================================
# 配置
# ============================================================================

DEFAULT_CONFIG = {
    "port": 3000,
    "user_id": 42,
    "github_login": "test-user",
    "plan": "zed_pro",  # zed_free, zed_pro, zed_pro_trial
    "trial_started_at": None,
    "account_too_young": False,
    "overdue_invoices": False,
    "edit_prediction_limit": 2000,
}


def make_user_response(config):
    return {
        "user": {
            "id": config["user_id"],
            "metrics_id": str(uuid.uuid4()),
            "avatar_url": f"https://avatars.githubusercontent.com/u/{config['user_id']}",
            "github_login": config["github_login"],
            "name": f"Mock User ({config['github_login']})",
            "is_staff": False,
            "accepted_tos_at": "2024-01-01T00:00:00.000Z",
            "has_connected_to_collab_once": True,
        },
        "feature_flags": [],
        "organizations": [
            {
                "id": {"0": f"org-{config['user_id']}"},
                "name": f"{config['github_login']}'s Organization",
                "is_personal": True,
            }
        ],
        "default_organization_id": {"0": f"org-{config['user_id']}"},
        "plans_by_organization": {f"org-{config['user_id']}": {"known": config["plan"]}},
        "configuration_by_organization": {
            f"org-{config['user_id']}": {
                "is_zed_model_provider_enabled": True,
                "is_agent_thread_feedback_enabled": True,
                "is_collaboration_enabled": True,
                "edit_prediction": {"is_enabled": True, "is_feedback_enabled": True},
            }
        },
        "plan": {
            "plan_v3": {"known": config["plan"]},
            "subscription_period": None,
            "usage": {
                "edit_predictions": {"used": 0, "limit": str(config["edit_prediction_limit"])}
            },
            "trial_started_at": config["trial_started_at"],
            "is_account_too_young": config["account_too_young"],
            "has_overdue_invoices": config["overdue_invoices"],
        },
    }


DEFAULT_MODELS = [
    {
        "provider": "anthropic",
        "id": {"0": "claude-sonnet-4-20250514"},
        "display_name": "Claude Sonnet 4",
        "is_latest": True,
        "max_token_count": 200000,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_images": True,
        "supports_thinking": True,
        "supports_disabling_thinking": True,
        "supports_fast_mode": False,
        "supported_effort_levels": [
            {"name": {"0": "None"}, "value": {"0": "none"}, "is_default": True},
            {"name": {"0": "Low"}, "value": {"0": "low"}, "is_default": None},
            {"name": {"0": "Medium"}, "value": {"0": "medium"}, "is_default": None},
            {"name": {"0": "High"}, "value": {"0": "high"}, "is_default": None},
        ],
        "supports_streaming_tools": True,
        "supports_parallel_tool_calls": False,
    },
    {
        "provider": "anthropic",
        "id": {"0": "claude-opus-4-8"},
        "display_name": "Claude Opus 4.8",
        "is_latest": False,
        "max_token_count": 200000,
        "max_output_tokens": 4096,
        "supports_tools": True,
        "supports_images": True,
        "supports_thinking": True,
        "supports_disabling_thinking": False,
        "supports_fast_mode": True,
        "supported_effort_levels": [
            {"name": {"0": "None"}, "value": {"0": "none"}, "is_default": True},
            {"name": {"0": "Low"}, "value": {"0": "low"}, "is_default": None},
            {"name": {"0": "Medium"}, "value": {"0": "medium"}, "is_default": None},
            {"name": {"0": "High"}, "value": {"0": "high"}, "is_default": None},
        ],
        "supports_streaming_tools": True,
        "supports_parallel_tool_calls": False,
    },
    {
        "provider": "open_ai",
        "id": {"0": "gpt-4o"},
        "display_name": "GPT-4o",
        "is_latest": True,
        "max_token_count": 128000,
        "max_output_tokens": 16384,
        "supports_tools": True,
        "supports_images": True,
        "supports_thinking": False,
        "supports_disabling_thinking": False,
        "supports_fast_mode": False,
        "supported_effort_levels": [],
        "supports_streaming_tools": False,
        "supports_parallel_tool_calls": True,
    },
    {
        "provider": "google",
        "id": {"0": "gemini-2.5-pro"},
        "display_name": "Gemini 2.5 Pro",
        "is_latest": True,
        "max_token_count": 1048576,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_images": True,
        "supports_thinking": True,
        "supports_disabling_thinking": True,
        "supports_fast_mode": False,
        "supported_effort_levels": [],
        "supports_streaming_tools": False,
        "supports_parallel_tool_calls": False,
    },
    {
        "provider": "x_ai",
        "id": {"0": "grok-3"},
        "display_name": "Grok 3",
        "is_latest": True,
        "max_token_count": 131072,
        "max_output_tokens": 8192,
        "supports_tools": True,
        "supports_images": True,
        "supports_thinking": False,
        "supports_disabling_thinking": False,
        "supports_fast_mode": False,
        "supported_effort_levels": [],
        "supports_streaming_tools": False,
        "supports_parallel_tool_calls": True,
    },
]


# ============================================================================
# HTTP Handler
# ============================================================================

class MockHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器 — 用标准库实现，无外部依赖"""

    # 类级状态（所有实例共享）
    config = dict(DEFAULT_CONFIG)
    request_log = []

    def log_message(self, format, *args):
        pass  # 不打印默认日志

    def _send_json(self, data, status=200, extra_headers=None):
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        if extra_headers:
            for k, v in extra_headers.items():
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 0:
            return json.loads(self.rfile.read(length))
        return {}

    def _log(self):
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": self.command,
            "path": self.path,
        }
        self.__class__.request_log.append(entry)
        safe_headers = {k: v for k, v in self.headers.items()
                        if k.lower() not in ("authorization", "cookie", "x-api-key", "proxy-authorization")}
        logger.info(f"{self.command} {self.path}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        self._log()

        if path == "/_mock/status":
            self._send_json({
                "status": "running",
                "config": {k: v for k, v in self.config.items() if k != "access_token"},
                "requests_served": len(self.__class__.request_log),
            })

        elif path == "/_mock/logs":
            self._send_json(self.__class__.request_log[-100:])

        elif path == "/client/users/me":
            auth = self.headers.get("Authorization", "")
            if not auth:
                self._send_json({"error": "Missing authorization"}, 401)
            else:
                self._send_json(make_user_response(self.config))

        elif path == "/models":
            self._send_json({
                "models": DEFAULT_MODELS,
                "default_model": {"0": "claude-sonnet-4-20250514"},
                "default_fast_model": None,
                "recommended_models": [
                    {"0": "claude-sonnet-4-20250514"},
                    {"0": "gpt-4o"},
                    {"0": "gemini-2.5-pro"},
                ],
            })

        elif path == "/native_app_signin_succeeded":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Login successful</h1></body></html>")

        elif path.startswith("/native_app_signin"):
            # OAuth 回调处理
            qs = parse_qs(parsed.query)
            port = qs.get("native_app_port", [None])[0]
            public_key = qs.get("native_app_public_key", [None])[0]
            system_id = qs.get("system_id", [None])[0]

            if not port or not public_key:
                self._send_json({"error": "Missing oauth params"}, 400)
                return

            # 生成 access_token 并加密
            access_token = random_token()
            self.config["access_token"] = access_token  # 保存备查

            from cryptography.hazmat.primitives import serialization, hashes
            from cryptography.hazmat.primitives.asymmetric import padding
            import base64

            der_bytes = base64.urlsafe_b64decode(public_key)
            pub_key = serialization.load_der_public_key(der_bytes)
            encrypted = pub_key.encrypt(
                access_token.encode(),
                padding.OAEP(
                    mgf=padding.MGF1(algorithm=hashes.SHA256()),
                    algorithm=hashes.SHA256(),
                    label=None,
                ),
            )
            encrypted_b64 = base64.urlsafe_b64encode(encrypted).decode()

            # 回调客户端
            import urllib.request
            callback_url = f"http://127.0.0.1:{port}/?user_id={self.config['user_id']}&access_token={encrypted_b64}"
            try:
                urllib.request.urlopen(callback_url, timeout=5)
                self._send_json({"status": "ok", "user_id": self.config["user_id"]})
            except Exception as e:
                logger.warning(f"OAuth callback failed: {e}")
                self._send_json({"error": str(e)}, 502)

        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        self._log()
        body = self._read_body()

        if path == "/client/llm_tokens":
            auth = self.headers.get("Authorization", "")
            if not auth:
                self._send_json({"error": "Invalid Authorization header"}, 401)
                return

            org_id = body.get("organization_id", "unknown")
            llm_token = f"zed_llm_mock_{uuid.uuid4().hex}"
            self._send_json({"token": {"0": llm_token}})

        elif path == "/client/system_settings":
            self._send_json({"selected_organization_id": {"0": f"org-{self.config['user_id']}"}})

        elif path == "/completions":
            auth = self.headers.get("Authorization", "")
            if not auth:
                self._send_json({"error": "Unauthorized"}, 401)
                return

            provider = body.get("provider", "unknown")
            model = body.get("model", "unknown")

            if self.config["plan"] == "zed_free":
                self._send_json({
                    "code": "payment_required",
                    "message": "You reached your free usage limit. Upgrade to Zed Pro for more prompts."
                }, 402)
                return

            # 流式响应
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("x-zed-server-supports-status-messages", "true")
            self.send_header("x-zed-client-supports-stream-ended-request-completion-status", "true")
            self.send_header("Connection", "close")
            self.end_headers()

            def write(line):
                self.wfile.write((json.dumps(line) + "\n").encode())
                self.wfile.flush()

            write({"Status": {"Queued": {"position": 0}}})
            write({"Status": "Started"})

            if provider == "anthropic":
                write({"Event": {"type": "message_start", "message": {
                    "id": f"msg_{uuid.uuid4().hex[:24]}", "type": "message",
                    "role": "assistant", "content": [],
                    "model": model, "stop_reason": None, "stop_sequence": None,
                    "usage": {"input_tokens": 10, "output_tokens": 1}}}})
                write({"Event": {"type": "content_block_start", "index": 0,
                                "content_block": {"type": "text", "text": ""}}})
                write({"Event": {"type": "content_block_delta", "index": 0,
                                "delta": {"type": "text_delta",
                                          "text": "Hello from Zed Mock! Your protocol analysis is verified ✅"}}})
                write({"Event": {"type": "content_block_stop", "index": 0}})
                write({"Event": {"type": "message_delta",
                                "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                                "usage": {"output_tokens": 15}}})
                write({"Event": {"type": "message_stop"}})
            else:
                write({"Event": {"type": "text", "text": f"Mock response from {provider}/{model}"}})

            write({"Status": "StreamEnded"})

            # 显式关闭连接，通知客户端流已结束（ndjson 无终止符，需 EOF 才能触发 iter_lines 结束）
            self.close_connection = True

        elif path in (
            "/client/feedback/agent_thread",
            "/client/feedback/agent_thread_comments",
            "/client/feedback/edit_prediction",
        ):
            self._send_json({"status": "ok"})

        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_PATCH(self):
        self._log()
        if "/client/system_settings" in self.path:
            self._send_json({"selected_organization_id": {"0": f"org-{self.config['user_id']}"}})
        else:
            self._send_json({"error": "Not Found"}, 404)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()


# ============================================================================
# 入口
# ============================================================================

def setup_development_credentials(config):
    """写入开发凭证文件"""
    creds_dir = Path.home() / ".config" / "zed"
    creds_dir.mkdir(parents=True, exist_ok=True)
    creds_path = creds_dir / "development_credentials"

    access_token = random_token()
    credentials = {"https://zed.dev": [str(config["user_id"]), access_token]}
    with open(creds_path, "w") as f:
        json.dump(credentials, f)

    logger.info(f"开发凭证已写入: {creds_path}")
    logger.info(f"  user_id: {config['user_id']}")
    logger.info(f"  access_token fingerprint: {token_fingerprint(access_token)}")

    config["access_token"] = access_token
    return creds_path


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Zed Cloud API Mock Server")
    parser.add_argument("--port", type=int, default=3000, help="监听端口")
    parser.add_argument("--plan", default="zed_pro", choices=["zed_free", "zed_pro", "zed_pro_trial"])
    parser.add_argument("--user-id", type=int, default=42)
    parser.add_argument("--login", default="test-user")
    parser.add_argument("--no-creds", action="store_true", help="不设置开发凭证")
    parser.add_argument("--xvfb", action="store_true", help="启动虚拟显示")
    args = parser.parse_args()

    # 更新配置
    MockHandler.config.update({
        "port": args.port,
        "plan": args.plan,
        "user_id": args.user_id,
        "github_login": args.login,
    })

    # 设置开发凭证
    if not args.no_creds:
        setup_development_credentials(MockHandler.config)

    # 可选：启动虚拟显示
    if args.xvfb:
        import subprocess
        display_num = 99
        proc = subprocess.Popen(
            ["Xvfb", f":{display_num}", "-screen", "0", "1920x1080x24"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
        os.environ["DISPLAY"] = f":{display_num}"
        logger.info(f"虚拟显示已启动: :{display_num}")

    # 启动服务
    server = HTTPServer(("0.0.0.0", args.port), MockHandler)

    logger.info(f"\n{'='*60}")
    logger.info(f"🚀 Zed Cloud Mock Server")
    logger.info(f"   端口: {args.port}")
    logger.info(f"   计划: {args.plan}")
    logger.info(f"   用户: {args.login} (ID: {args.user_id})")
    logger.info(f"{'='*60}")
    logger.info(f"")
    logger.info(f"启动 Zed 连接此 Mock:")
    logger.info(f"  ZED_DEVELOPMENT_USE_KEYCHAIN=true \\")
    logger.info(f"  ZED_SERVER_URL=http://localhost:{args.port} \\")
    logger.info(f"  ./zed.app/libexec/zed-editor")
    logger.info(f"")
    logger.info(f"诊断端点:")
    logger.info(f"  http://localhost:{args.port}/_mock/status")
    logger.info(f"  http://localhost:{args.port}/_mock/logs")
    logger.info(f"")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务停止")
        server.server_close()


if __name__ == "__main__":
    main()