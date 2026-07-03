#!/usr/bin/env python3
"""
Zed OAuth 全自动化流程
======================
使用 Playwright 无头浏览器自动化完成 GitHub OAuth 授权，
获取真实的 cloud.zed.dev access_token 并验证 API。

用法:
  1. 设置环境变量:
     export GITHUB_USER="your_github_username"
     export GITHUB_PASS="your_github_password"
     export GITHUB_2FA="optional_2fa_code"  # 如果有 2FA

  2. 运行:
     python3 scripts/zed_auth_flow.py --all

  3. 脚本会:
     1. 自动打开 GitHub OAuth 页面
     2. 填写账号密码
     3. 完成授权
     4. 获取 access_token
     5. 调用 /client/users/me
     6. 获取 LLM Token
     7. 获取模型列表
     8. 可选: 测试 /completions
"""

import base64
import hashlib
import json
import logging
import os
import secrets
import sys
import time
import urllib.parse
import uuid
from datetime import datetime, timezone
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from threading import Thread, Event
from typing import Optional
from urllib.parse import urlencode, urlparse, parse_qs
from getpass import getpass

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("zed_oauth")

CLOUD_API = "https://cloud.zed.dev"
ZED_WEB = "https://zed.dev"


def token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()[:12]


def random_token() -> str:
    return base64.urlsafe_b64encode(os.urandom(48)).decode("ascii")


def generate_keypair():
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend(),
    )
    return private_key.public_key(), private_key


def serialize_public_key(public_key) -> str:
    der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.PKCS1,
    )
    return base64.urlsafe_b64encode(der).decode("ascii")


def decrypt_access_token(private_key, encrypted_b64: str) -> str:
    encrypted = base64.urlsafe_b64decode(encrypted_b64)
    for pad in [
        padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None),
        padding.PKCS1v15(),
    ]:
        try:
            return private_key.decrypt(encrypted, pad).decode("utf-8")
        except Exception:
            continue
    raise ValueError("解密失败")


# ============================================================================
# 回调服务器
# ============================================================================

# 回调服务器（带 CSRF state 保护）

callback_result = {}
callback_event = Event()
callback_state = ""

class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        uid = qs.get("user_id", [None])[0]
        token = qs.get("access_token", [None])[0]
        state = qs.get("state", [None])[0]

        # CSRF 保护：验证 state 参数
        if callback_state and state != callback_state:
            logger.warning("CSRF 检测失败：state 参数不匹配")
            self.send_response(403)
            self.end_headers()
            return

        if uid and token:
            callback_result["user_id"] = uid
            callback_result["access_token"] = token
            callback_event.set()
            self.send_response(302)
            self.send_header("Location", "https://zed.dev/native_app_signin_succeeded")
            self.end_headers()
        else:
            self.send_response(400)
            self.end_headers()
        self.server._got_request = True

    def log_message(self, format, *args):
        pass


# ============================================================================
# Playwright OAuth 自动化
# ============================================================================

def do_oauth(github_user: str, github_pass: str, callback_port: int, public_key_b64: str) -> dict:
    """
    完整 OAuth 流程:
    1. 打开 native_app_signin URL → 自动跳转到 GitHub OAuth 页
    2. 填写 GitHub 账号密码
    3. 处理授权确认
    4. 等待回调到 localhost
    """
    from playwright.sync_api import sync_playwright, TimeoutError as PwTimeout

    auth_url = "{}?{}".format(
        ZED_WEB + "/native_app_signin",
        urlencode({
            "native_app_port": callback_port,
            "native_app_public_key": public_key_b64,
            "system_id": str(uuid.uuid4()),
            "state": callback_state,
        }),
    )

    logger.info(f"导航到 OAuth 起始页...")
    logger.info(f"  URL: {auth_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        )
        page = ctx.new_page()

        # 监听所有新页面（可能是 popup）
        captured = {}

        def on_response(resp):
            url = resp.url
            if url.startswith(f"http://127.0.0.1:{callback_port}"):
                # 脱敏处理：移除 access_token 参数
                parsed = urllib.parse.urlparse(url)
                qs = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
                if "access_token" in qs:
                    qs["access_token"] = ["<REDACTED>"]
                    parsed = parsed._replace(query=urllib.parse.urlencode(qs, doseq=True))
                safe_url = urllib.parse.urlunparse(parsed)
                captured["callback"] = url
                logger.info(f"✅ 捕获回调: {safe_url[:120]}...")

        page.on("response", on_response)

        # 导航
        page.goto(auth_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(2000)

        # 此时应该已经在 GitHub 登录页
        logger.info(f"页面 URL: {page.url[:100]}...")
        logger.info(f"页面标题: {page.title()}")

        # 检查是否在 GitHub 登录页
        if "github.com/login" in page.url:
            logger.info("在 GitHub 登录页面，填写表单...")

            # 等待表单加载
            page.wait_for_selector("#login_field", timeout=10000)

            # 填写用户名
            page.locator("#login_field").fill(github_user)
            logger.info("已填写用户名")

            # 填写密码
            page.locator("#password").fill(github_pass)
            logger.info("已填写密码")

            # 提交
            page.locator("input[type='submit']").click()
            logger.info("已提交登录表单")

            page.wait_for_timeout(3000)

            # 处理 2FA
            if "two-factor" in page.url.lower() or "2fa" in page.url.lower():
                logger.info("检测到 2FA 页面，需要验证码")
                twofa = os.environ.get("GITHUB_2FA", "")
                if not twofa:
                    twofa = input("GitHub 2FA 验证码: ")
                if twofa:
                    otp_input = page.locator("#otp").first
                    if otp_input.is_visible(timeout=3000):
                        otp_input.fill(twofa)
                        page.locator("button:has-text('Verify')").click()
                        logger.info("已提交 2FA 验证码")
                        page.wait_for_timeout(3000)

            # 处理授权确认页
            try:
                auth_btn = page.locator("button:has-text('Authorize')").first
                if auth_btn.is_visible(timeout=3000):
                    logger.info("检测到授权确认页")
                    # 确认 scope
                    auth_btn.click()
                    logger.info("已点击 Authorize")
                    page.wait_for_timeout(3000)
            except Exception:
                pass

            # 等待回调
            logger.info("等待 OAuth 回调...")
            wait_start = time.time()
            while time.time() - wait_start < 60:
                if "callback" in captured:
                    url = captured["callback"]
                    qs = parse_qs(urlparse(url).query)
                    return {
                        "user_id": qs.get("user_id", [""])[0],
                        "access_token": qs.get("access_token", [""])[0],
                    }
                time.sleep(0.5)

            raise TimeoutError("未捕获到回调")

        else:
            logger.info(f"页面不在 GitHub 登录页，当前 URL: {page.url}")
            logger.info(f"页面内容: {page.locator('body').inner_text()[:500]}")

        browser.close()

    raise Exception("OAuth 流程未完成")


# ============================================================================
# Cloud API 调用
# ============================================================================

def api_call(method: str, path: str, headers: dict, body: bytes = None, timeout=15):
    """调用 cloud.zed.dev API"""
    import urllib.request
    import urllib.error

    url = f"{CLOUD_API}{path}"
    req = urllib.request.Request(
        url, data=body,
        headers={"User-Agent": "Zed/1.6.3", **headers},
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def test_user(uid: int, token: str):
    status, headers, body = api_call("GET", "/client/users/me", {
        "Authorization": f"{uid} {token}", "Content-Type": "application/json",
    })
    logger.info(f"  HTTP {status}")
    if status == 200:
        d = json.loads(body)
        plan = d.get("plan", {})
        pv = plan.get("plan_v3", {})
        if isinstance(pv, dict): pv = pv.get("known", "?")
        u = d.get("user", {})
        orgs = d.get("organizations", [])
        default_org = d.get("default_organization_id", {})
        if isinstance(default_org, dict): default_org = default_org.get("0")
        logger.info(f"  GitHub: {u.get('github_login','?')}  Plan: {pv}")
        logger.info(f"  Trial: {plan.get('trial_started_at','N/A')}")
        logger.info(f"  组织: {len(orgs)}, 默认: {default_org}")
        return d, default_org
    else:
        logger.info(f"  Body: {body[:200]}")
        return None, None


def test_llm_token(uid: int, token: str, org_id: str):
    body = json.dumps({"organization_id": org_id}).encode()
    status, headers, body = api_call("POST", "/client/llm_tokens", {
        "Authorization": f"{uid} {token}", "Content-Type": "application/json",
    }, body)
    logger.info(f"  HTTP {status}")
    if status == 200:
        d = json.loads(body)
        t = d.get("token", {})
        if isinstance(t, dict): t = t.get("0", "")
        logger.info(f"  Token fingerprint: {token_fingerprint(t)}")
        return t
    else:
        logger.info(f"  Body: {body[:300]}")
        return None


def test_models(llm_token: str):
    status, headers, body = api_call("GET", "/models", {
        "Authorization": f"Bearer {llm_token}",
        "x-zed-client-supports-x-ai": "true",
    })
    logger.info(f"  HTTP {status}")
    if status == 200:
        d = json.loads(body)
        models = d.get("models", [])
        logger.info(f"  模型数: {len(models)}")
        for m in models[:5]:
            mid = m.get("id", {})
            if isinstance(mid, dict): mid = mid.get("0", "?")
            logger.info(f"    {m.get('provider','?')}/{m.get('display_name',mid)}")
        return d
    else:
        logger.info(f"  Body: {body[:200]}")
        return None


def test_completion(llm_token: str):
    body = json.dumps({
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "provider_request": {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 50,
            "messages": [{"role": "user", "content": [{"type": "text", "text": "Reply: OK"}]}],
            "stream": True,
        },
    }).encode()
    status, headers, body = api_call("POST", "/completions", {
        "Authorization": f"Bearer {llm_token}",
        "Content-Type": "application/json",
        "x-zed-client-supports-status-messages": "true",
        "x-zed-client-supports-stream-ended-request-completion-status": "true",
    }, body, timeout=30)
    logger.info(f"  HTTP {status}")
    if status == 200:
        lines = [l for l in body.decode().split("\n") if l.strip()]
        logger.info(f"  收到 {len(lines)} 行事件")
        for line in lines[:8]:
            try:
                evt = json.loads(line)
                if "Status" in evt:
                    logger.info(f"    Status: {str(evt['Status'])[:80]}")
                elif "Event" in evt:
                    e = evt["Event"]
                    if isinstance(e, dict) and e.get("type") == "content_block_delta":
                        txt = e.get("delta", {}).get("text", "")
                        if txt: logger.info(f"    → {txt}")
                    else:
                        logger.info(f"    Event: {str(e)[:80]}")
            except Exception:
                logger.info(f"    RAW: {line[:80]}")
        return body.decode()
    elif status == 402:
        logger.info(f"  402 Payment Required (Free plan)")
        return None
    else:
        logger.info(f"  Body: {body[:300]}")
        return None


# ============================================================================
# 主入口
# ============================================================================

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Zed OAuth 全自动化")
    parser.add_argument("--all", action="store_true", help="完整流程: OAuth → API 验证 → Completion")
    parser.add_argument("--oauth-only", action="store_true", help="仅 OAuth 登录")
    parser.add_argument("--save", action="store_true", help="保存凭证到 development_credentials")
    parser.add_argument("--uid", type=int, help="跳过 OAuth，直接指定 user_id")
    parser.add_argument("--token", help="跳过 OAuth，直接指定 access_token")
    parser.add_argument("--llm-token", help="跳过所有认证，直接用 LLM Token")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Zed OAuth 全自动化流程")
    logger.info("=" * 60)

    uid = args.uid
    access_token = args.token
    llm_token = args.llm_token

    # ---- Phase 1: OAuth ----
    if not llm_token and not (uid and access_token):
        logger.info("\n[Phase 1] GitHub OAuth 登录")

        gu = os.environ.get("GITHUB_USER", "")
        gp = os.environ.get("GITHUB_PASS", "")
        if not gu: gu = input("GitHub 用户名/邮箱: ")
        if not gp: gp = getpass("GitHub 密码: ")

        logger.info("1. 生成 RSA 密钥对")
        pub_key, priv_key = generate_keypair()
        pub_b64 = serialize_public_key(pub_key)

        logger.info("2. 启动回调服务器")
        callback_event.clear()
        callback_result.clear()
        callback_state = secrets.token_urlsafe(32)
        server = HTTPServer(("127.0.0.1", 0), CallbackHandler)
        port = server.server_address[1]
        t = Thread(target=server.serve_forever, daemon=True)
        t.start()

        logger.info("3. 执行 Playwright OAuth 自动化")
        try:
            result = do_oauth(gu, gp, port, pub_b64)
        finally:
            server.shutdown()

        encrypted_token = result.get("access_token", "")
        uid = int(result.get("user_id", 0))

        logger.info("4. 解密 access_token")
        access_token = decrypt_access_token(priv_key, encrypted_token)
        logger.info(f"   User ID: {uid}")
        logger.info(f"   Token fingerprint: {token_fingerprint(access_token)}")

        if args.save:
            creds_path = Path.home() / ".config" / "zed" / "development_credentials"
            creds_path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(creds_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, 'w') as f:
                f.write(json.dumps({"https://zed.dev": [str(uid), access_token]}))
            logger.info(f"   凭证已保存到: {creds_path}")

    # ---- Phase 2: API 验证 ----
    if llm_token:
        logger.info("\n[Phase 2] 已有 LLM Token，直接验证")
        test_models(llm_token)
        if args.all:
            test_completion(llm_token)
    elif uid and access_token:
        logger.info("\n[Phase 2] 验证 cloud.zed.dev API")
        user_data, org_id = test_user(uid, access_token)
        if user_data and org_id:
            logger.info("\n  获取 LLM Token...")
            llm_token = test_llm_token(uid, access_token, org_id)
            if llm_token:
                logger.info("\n  模型列表...")
                test_models(llm_token)
                if args.all:
                    logger.info("\n  Completion 测试...")
                    test_completion(llm_token)

    logger.info("\n" + "=" * 60)
    logger.info("✅ 流程完成")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()