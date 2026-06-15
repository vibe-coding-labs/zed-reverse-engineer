"""
Zed Authentication Flow - Python Implementation
===============================================
模拟 Zed 编辑器的完整 OAuth 登录 + LLM Token 获取流程。

基于对 Zed 源码的逆向分析，纯 Python 实现。

协议流程:
1. 生成 RSA 密钥对 (2048-bit)
2. 启动本地 HTTP 回调服务器
3. 打开浏览器访问 zed.dev/native_app_signin
4. 用户通过 GitHub OAuth 授权
5. 浏览器回调本地服务器，返回加密的 access_token
6. 用私钥解密 access_token
7. 用 user_id + access_token 调用 API:
   - GET /client/users/me  → 获取用户信息和 plan
   - POST /client/llm_tokens → 获取 LLM Bearer Token
8. 用 Bearer Token 调用 POST /completions

依赖: pip install cryptography requests flask
"""

import base64
import json
import logging
import os
import platform
import secrets
import subprocess
import sys
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlencode, urlparse

import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger("zed_auth")

# ============================================================================
# 配置
# ============================================================================

ZED_SERVER_URL = os.environ.get("ZED_SERVER_URL", "https://zed.dev")
CLOUD_API_URL = os.environ.get("ZED_CLOUD_API_URL", "https://cloud.zed.dev")
LLM_API_URL = os.environ.get("ZED_LLM_API_URL", "https://cloud.zed.dev")

# Zed 版本信息
ZED_VERSION = "1.6.3"
RELEASE_CHANNEL = "stable"
SYSTEM_ID = str(uuid.uuid4())


# ============================================================================
# 数据结构
# ============================================================================

@dataclass
class Credentials:
    """用户凭证，对应 Rust 的 Credentials { user_id, access_token }"""
    user_id: int
    access_token: str  # RSA 解密后的明文 token


@dataclass
class LlmToken:
    """LLM API Token，对应 Rust 的 LlmApiToken / LlmToken"""
    token: str
    organization_id: str


@dataclass
class PlanInfo:
    """用户计划信息，对应 Rust 的 PlanInfo"""
    plan: str                     # zed_free / zed_pro / zed_pro_trial / zed_business
    trial_started_at: Optional[str]  # RFC3339 or None
    is_account_too_young: bool
    has_overdue_invoices: bool
    edit_predictions_used: int = 0
    edit_predictions_limit: str = "2000"  # "2000" or "unlimited"


@dataclass
class UserInfo:
    """用户信息，对应 Rust 的 GetAuthenticatedUserResponse"""
    id: int
    github_login: str
    avatar_url: str
    name: Optional[str]
    is_staff: bool
    plan: PlanInfo
    organizations: list = field(default_factory=list)
    default_organization_id: Optional[str] = None


# ============================================================================
# RSA 加密工具 (对应 Rust rpc::auth)
# ============================================================================

def generate_keypair() -> tuple:
    """
    生成 RSA 2048-bit 密钥对。

    对应 Rust: rpc::auth::keypair()
    - RSA 2048-bit
    - 公钥以 PKCS#1 DER 编码后 base64url 序列化
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )
    public_key = private_key.public_key()
    return public_key, private_key


def serialize_public_key(public_key) -> str:
    """
    将公钥序列化为 base64url 字符串。

    对应 Rust: String::try_from(PublicKey)
    - PKCS#1 DER 编码 → base64url
    """
    der_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.PKCS1,
    )
    return base64.urlsafe_b64encode(der_bytes).decode("ascii")


def decrypt_access_token(private_key, encrypted_b64: str) -> str:
    """
    解密 access_token。

    对应 Rust: PrivateKey::decrypt_string()
    - base64url 解码
    - 先尝试 OAEP-SHA256 (V1) 解密
    - 失败后尝试 PKCS1v15 (V0) 解密
    """
    encrypted_bytes = base64.urlsafe_b64decode(encrypted_b64)

    try:
        # V1: OAEP with SHA-256
        plaintext = private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None,
            ),
        )
        return plaintext.decode("utf-8")
    except Exception:
        pass

    try:
        # V0: PKCS1v15 fallback
        plaintext = private_key.decrypt(
            encrypted_bytes,
            padding.PKCS1v15(),
        )
        return plaintext.decode("utf-8")
    except Exception as e:
        raise ValueError(f"Failed to decrypt access token: {e}")


def random_token() -> str:
    """
    生成随机 token (用于测试)。

    对应 Rust: rpc::auth::random_token()
    - 48 字节随机数 → base64url
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(48)).decode("ascii")


# ============================================================================
# Zed Cloud API 客户端
# ============================================================================

def build_auth_header(user_id: int, access_token: str) -> str:
    """
    构建 Authorization header。

    对应 Rust: build_request() 中的
    Authorization: "{user_id} {access_token}"
    """
    return f"{user_id} {access_token}"


def get_authenticated_user(
    user_id: int,
    access_token: str,
    system_id: Optional[str] = None,
) -> UserInfo:
    """
    获取当前用户信息。

    GET {cloud_api_url}/client/users/me
    Authorization: {user_id} {access_token}

    对应 Rust: CloudApiClient::get_authenticated_user()
    """
    url = f"{CLOUD_API_URL}/client/users/me"
    headers = {
        "Authorization": build_auth_header(user_id, access_token),
        "Content-Type": "application/json",
    }
    if system_id:
        headers["x-zed-system-id"] = system_id

    logger.info(f"GET {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    plan_data = data.get("plan", {})
    plan_v3 = plan_data.get("plan_v3", "zed_free")
    if isinstance(plan_v3, dict):
        # KnownOrUnknown 格式
        plan_v3 = plan_v3.get("known", "zed_free")

    usage = plan_data.get("usage", {})
    edit_prediction_usage = usage.get("edit_predictions", {})

    plan = PlanInfo(
        plan=plan_v3,
        trial_started_at=plan_data.get("trial_started_at"),
        is_account_too_young=plan_data.get("is_account_too_young", False),
        has_overdue_invoices=plan_data.get("has_overdue_invoices", False),
        edit_predictions_used=edit_prediction_usage.get("used", 0),
        edit_predictions_limit=edit_prediction_usage.get("limit", "2000"),
    )

    user_data = data.get("user", {})
    organizations = data.get("organizations", [])

    user_info = UserInfo(
        id=user_data.get("id", user_id),
        github_login=user_data.get("github_login", ""),
        avatar_url=user_data.get("avatar_url", ""),
        name=user_data.get("name"),
        is_staff=user_data.get("is_staff", False),
        plan=plan,
        organizations=[org.get("id", {}).get("0", "") for org in organizations],
        default_organization_id=data.get("default_organization_id", {}).get("0"),
    )

    return user_info


def create_llm_token(
    user_id: int,
    access_token: str,
    organization_id: str,
    system_id: Optional[str] = None,
) -> str:
    """
    获取 LLM Token。

    POST {cloud_api_url}/client/llm_tokens
    Authorization: {user_id} {access_token}
    Body: { "organization_id": "..." }

    对应 Rust: CloudApiClient::create_llm_token()
    """
    url = f"{CLOUD_API_URL}/client/llm_tokens"
    headers = {
        "Authorization": build_auth_header(user_id, access_token),
        "Content-Type": "application/json",
    }
    if system_id:
        headers["x-zed-system-id"] = system_id

    body = {"organization_id": organization_id}

    logger.info(f"POST {url} (org={organization_id})")
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    # token 格式: {"token": {"0": "llm_token_string"}}
    token = data.get("token", {})
    if isinstance(token, dict) and "0" in token:
        return token["0"]
    if isinstance(token, str):
        return token
    return str(token)


def list_models(
    llm_token: str,
    system_id: Optional[str] = None,
) -> dict:
    """
    获取可用模型列表。

    GET {llm_api_url}/models
    Authorization: Bearer {llm_token}

    对应 Rust: CloudModelProvider::fetch_models_request()
    """
    url = f"{LLM_API_URL}/models"
    headers = {
        "Authorization": f"Bearer {llm_token}",
        "x-zed-client-supports-x-ai": "true",
    }
    if system_id:
        headers["x-zed-system-id"] = system_id

    logger.info(f"GET {url}")
    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def stream_completion(
    llm_token: str,
    provider: str,
    model: str,
    provider_request: dict,
    thread_id: Optional[str] = None,
    prompt_id: Optional[str] = None,
    system_id: Optional[str] = None,
):
    """
    发送 LLM Completion 请求（流式）。

    POST {llm_api_url}/completions
    Authorization: Bearer {llm_token}

    对应 Rust: CloudLanguageModel::perform_llm_completion()
    """
    url = f"{LLM_API_URL}/completions"
    headers = {
        "Authorization": f"Bearer {llm_token}",
        "Content-Type": "application/json",
        "x-zed-version": ZED_VERSION,
        "x-zed-client-supports-status-messages": "true",
        "x-zed-client-supports-stream-ended-request-completion-status": "true",
    }
    if system_id:
        headers["x-zed-system-id"] = system_id

    body = {
        "provider": provider,
        "model": model,
        "provider_request": provider_request,
    }
    if thread_id:
        body["thread_id"] = thread_id
    if prompt_id:
        body["prompt_id"] = prompt_id

    logger.info(f"POST {url} (model={model})")
    resp = requests.post(url, headers=headers, json=body, stream=True, timeout=120)

    if resp.status_code == 402:
        logger.error("402 Payment Required - 需要升级 Pro 或额度已用完")
        return None

    resp.raise_for_status()

    # 流式读取响应（JSON Lines）
    for line in resp.iter_lines(decode_unicode=True):
        if line:
            yield json.loads(line)

    # 检查是否包含 x-zed-expired-token 或 x-zed-outdated-token 头
    if resp.headers.get("x-zed-expired-token"):
        logger.warning("LLM token expired, need to refresh")
    if resp.headers.get("x-zed-outdated-token"):
        logger.warning("LLM token outdated, need to refresh")


# ============================================================================
# 完整认证流程 — 浏览器 OAuth
# ============================================================================

class OAuthCallbackServer:
    """
    启动本地 HTTP 服务器接收 OAuth 回调。

    对应 Rust: authenticate_with_browser()
    - 绑定 127.0.0.1:随机端口
    - 等待浏览器回调（最多 100 秒）
    - 返回 user_id 和加密的 access_token
    """

    def __init__(self):
        self._server = None
        self._thread = None
        self.port = 0

    def start(self):
        from http.server import HTTPServer, BaseHTTPRequestHandler

        class CallbackHandler(BaseHTTPRequestHandler):
            callback_result = None
            callback_event = threading.Event()

            def do_GET(self):
                query = urlparse(self.path).query
                params = dict(p.split("=", 1) for p in query.split("&") if "=" in p)

                user_id = params.get("user_id")
                access_token = params.get("access_token")

                if user_id and access_token:
                    CallbackHandler.callback_result = {
                        "user_id": user_id,
                        "access_token": access_token,
                    }
                    CallbackHandler.callback_event.set()

                    # 302 重定向到成功页面
                    self.send_response(302)
                    self.send_header("Location", f"{ZED_SERVER_URL}/native_app_signin_succeeded")
                    self.end_headers()
                else:
                    self.send_response(400)
                    self.send_header("Content-Type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"Missing user_id or access_token")

            def log_message(self, format, *args):
                pass  # 不打印 HTTP 日志

        server = HTTPServer(("127.0.0.1", 0), CallbackHandler)
        self._server = server
        self.port = server.server_address[1]

        self._thread = threading.Thread(target=server.serve_forever, daemon=True)
        self._thread.start()

        logger.info(f"OAuth callback server listening on 127.0.0.1:{self.port}")
        return self.port

    def wait_for_callback(self, timeout: float = 100.0) -> dict:
        """等待浏览器回调，超时则抛出异常"""
        success = CallbackHandler.callback_event.wait(timeout=timeout)
        if not success:
            raise TimeoutError("OAuth callback timed out (waited {timeout}s)")
        return CallbackHandler.callback_result

    def stop(self):
        if self._server:
            self._server.shutdown()


def authenticate_via_browser() -> Credentials:
    """
    完整浏览器 OAuth 登录流程。

    1. 生成 RSA 密钥对
    2. 启动本地 HTTP 回调服务器
    3. 打开浏览器到 zed.dev/native_app_signin?port=...&public_key=...
    4. 用户登录 GitHub 授权
    5. 接收回调，解密 access_token
    6. 返回 Credentials
    """
    logger.info("=" * 60)
    logger.info("Step 1: 生成 RSA 密钥对")
    logger.info("=" * 60)
    public_key, private_key = generate_keypair()
    public_key_b64 = serialize_public_key(public_key)
    logger.info(f"Public key (base64url, {len(public_key_b64)} chars): {public_key_b64[:40]}...")

    logger.info("\n" + "=" * 60)
    logger.info("Step 2: 启动回调 HTTP 服务器")
    logger.info("=" * 60)
    server = OAuthCallbackServer()
    port = server.start()

    logger.info("\n" + "=" * 60)
    logger.info("Step 3: 打开浏览器进行 GitHub OAuth 登录")
    logger.info("=" * 60)

    params = {
        "native_app_port": port,
        "native_app_public_key": public_key_b64,
        "system_id": SYSTEM_ID,
    }
    auth_url = f"{ZED_SERVER_URL}/native_app_signin?{urlencode(params)}"

    logger.info(f"请在浏览器中打开以下链接:")
    logger.info(f"{auth_url}")
    logger.info("")

    # 尝试自动打开浏览器
    try:
        if platform.system() == "Darwin":
            subprocess.run(["open", auth_url])
        elif platform.system() == "Linux":
            subprocess.run(["xdg-open", auth_url])
        elif platform.system() == "Windows":
            # Windows: "start" is a cmd.exe built-in, shell=True required
            subprocess.run(["start", auth_url], shell=True)
    except Exception:
        pass

    logger.info("\n" + "=" * 60)
    logger.info("Step 4: 等待 OAuth 回调...")
    logger.info("=" * 60)

    try:
        callback = server.wait_for_callback(timeout=100.0)
        encrypted_token = callback["access_token"]
        user_id_str = callback["user_id"]
        logger.info(f"收到回调! user_id={user_id_str}")
    except TimeoutError:
        server.stop()
        raise
    finally:
        server.stop()

    logger.info("\n" + "=" * 60)
    logger.info("Step 5: 解密 access_token")
    logger.info("=" * 60)

    access_token = decrypt_access_token(private_key, encrypted_token)
    logger.info(f"Access token (前20位): {access_token[:20]}...")

    credentials = Credentials(
        user_id=int(user_id_str),
        access_token=access_token,
    )

    logger.info(f"\n✅ 登录成功! user_id={credentials.user_id}")
    return credentials


# ============================================================================
# 完整 LLM Token 获取流程
# ============================================================================

def get_llm_token_flow(
    credentials: Credentials,
    system_id: Optional[str] = None,
) -> tuple:
    """
    获取 LLM Token 的完整流程。

    1. 获取用户信息 / 组织
    2. 获取 LLM Token
    3. 获取可用模型列表
    """
    logger.info("\n" + "=" * 60)
    logger.info("Step 1: 获取用户信息 /client/users/me")
    logger.info("=" * 60)

    try:
        user_info = get_authenticated_user(
            credentials.user_id,
            credentials.access_token,
            system_id=system_id,
        )
        logger.info(f"  GitHub: {user_info.github_login}")
        logger.info(f"  Plan: {user_info.plan.plan}")
        logger.info(f"  Trial started: {user_info.plan.trial_started_at}")
        logger.info(f"  Account too young: {user_info.plan.is_account_too_young}")
        logger.info(f"  Has overdue invoices: {user_info.plan.has_overdue_invoices}")
        logger.info(f"  Edit predictions: {user_info.plan.edit_predictions_used}/{user_info.plan.edit_predictions_limit}")
        logger.info(f"  Organizations: {user_info.organizations}")
        logger.info(f"  Default org: {user_info.default_organization_id}")
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            logger.error("401 Unauthorized - 凭证无效")
        raise

    # 选择组织
    org_id = user_info.default_organization_id
    if not org_id and user_info.organizations:
        org_id = user_info.organizations[0]
    if not org_id:
        logger.error("没有可用的组织")
        raise ValueError("No organization found")

    logger.info("\n" + "=" * 60)
    logger.info(f"Step 2: 创建 LLM Token (org={org_id})")
    logger.info("=" * 60)

    try:
        llm_token_str = create_llm_token(
            credentials.user_id,
            credentials.access_token,
            org_id,
            system_id=system_id,
        )
        logger.info(f"  LLM Token: {llm_token_str[:20]}...")
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            logger.error("401 Unauthorized - 凭证过期或无效")
        raise

    logger.info("\n" + "=" * 60)
    logger.info("Step 3: 获取可用模型列表")
    logger.info("=" * 60)

    try:
        models_data = list_models(llm_token_str, system_id=system_id)
        models = models_data.get("models", [])
        default_model = models_data.get("default_model", {}).get("0", "N/A")
        logger.info(f"  可用模型 ({len(models)} 个):")
        for m in models:
            model_id = m.get("id", {}).get("0", "?")
            display = m.get("display_name", model_id)
            provider = m.get("provider", "?")
            logger.info(f"    [{provider}] {display} (id={model_id})")
        logger.info(f"\n  默认模型: {default_model}")
    except requests.HTTPError as e:
        if e.response.status_code == 402:
            logger.warning("402 Payment Required - 需要升级 Pro")
            models_data = None
        elif e.response.status_code == 401:
            logger.error("401 - LLM Token 无效")
            models_data = None
        else:
            raise
    except Exception as e:
        logger.warning(f"  获取模型列表失败: {e}")
        models_data = None

    return llm_token_str, user_info, models_data


async def main():
    """测试入口"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    # ================================================================
    # 方式 1: 浏览器 OAuth 登录（完整流程）
    # ================================================================
    # credentials = authenticate_via_browser()
    # llm_token, user_info, models = get_llm_token_flow(credentials)

    # ================================================================
    # 方式 2: 使用已有的 credentials（跳过浏览器）
    # 你首次登录后，凭证会保存在系统钥匙串中
    # 这里可以手动填入
    # ================================================================
    # credentials = Credentials(
    #     user_id=12345,
    #     access_token="your_access_token_here",
    # )
    # llm_token, user_info, models = get_llm_token_flow(credentials)

    # ================================================================
    # 方式 3: 仅验证 LLM Token（已有 token）
    # ================================================================
    # llm_token = "your_llm_token_here"
    # models = list_models(llm_token)
    # print(json.dumps(models, indent=2))

    # ================================================================
    # 方式 4: 测试 completion
    # ================================================================
    # for event in stream_completion(
    #     llm_token=llm_token,
    #     provider="anthropic",
    #     model="claude-sonnet-4-20250514",
    #     provider_request={
    #         "model": "claude-sonnet-4-20250514",
    #         "max_tokens": 1024,
    #         "messages": [
    #             {"role": "user", "content": [{"type": "text", "text": "Hello"}]}
    #         ],
    #         "stream": True,
    #     },
    # ):
    #     print(json.dumps(event))

    print("请在 main() 中设置 credentials 后运行")
    print("参考上方注释中的方式 2-4")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
