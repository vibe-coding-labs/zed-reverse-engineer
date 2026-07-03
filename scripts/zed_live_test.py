#!/usr/bin/env python3
"""
Zed 真实 API 测试脚本
======================
在你本地装了 Zed 并登录过的电脑上运行。
脚本会自动从 Zed 的凭证存储中读取真正的 credentials，然后调真实 cloud.zed.dev。

不需要把任何凭证发给我或其他地方，所有请求都只从你本地发出。

用法:
  python3 scripts/zed_live_test.py

输出:
  - 你的 Plan 类型（Free/Pro/Trial）
  - 组织 ID
  - LLM Token 能否获取
  - 模型列表
  - 可选：Completion 测试
"""

import json
import logging
import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("zed_live_test")

# ============================================================
# 从 Zed 本地存储读取凭证
# ============================================================

def find_zed_credentials():
    """
    尝试从各种位置读取 Zed 凭証。
    返回 (user_id, access_token) 或 None。
    """
    found = []

    # 方式 1: 开发凭证文件
    for config_dir in [
        Path.home() / ".config" / "zed",
        Path.home() / ".var/app/dev.zed.Zed/config/zed",  # Flatpak
    ]:
        creds_file = config_dir / "development_credentials"
        if creds_file.exists():
            try:
                data = json.loads(creds_file.read_text())
                for url, (uid, token) in data.items():
                    found.append(("development_credentials", uid, token))
            except Exception as e:
                logger.warning(f"  读取 {creds_file} 失败: {e}")

    # 方式 2: macOS 钥匙串
    if sys.platform == "darwin":
        try:
            import subprocess
            result = subprocess.run(
                ["security", "find-internet-password", "-s", "zed.dev", "-g"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                # 解析输出
                for line in result.stderr.split("\n"):
                    if '"acct"<blob>=' in line:
                        uid = line.split("=")[-1].strip().strip('"')
                    if "password" in line.lower() and "0x" in line:
                        token = line.split("=")[-1].strip()
                if uid and token:
                    found.append(("macOS keychain", uid, token))
        except Exception:
            pass

    # 方式 3: GNOME/libsecret (Linux)
    if sys.platform == "linux":
        try:
            import subprocess
            result = subprocess.run(
                ["secret-tool", "search", "server", "zed.dev"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                logger.info(f"  secret-tool 找到了条目")
        except FileNotFoundError:
            pass

    # 方式 4: 环境变量（手动注入）
    if os.environ.get("ZED_USER_ID") and os.environ.get("ZED_ACCESS_TOKEN"):
        found.append((
            "env vars",
            os.environ["ZED_USER_ID"],
            os.environ["ZED_ACCESS_TOKEN"],
        ))

    return found


# ============================================================
# 直接调真实 cloud.zed.dev
# ============================================================

CLOUD_API = "https://cloud.zed.dev"


def test_get_user(uid, token):
    """GET /client/users/me"""
    import urllib.request

    req = urllib.request.Request(
        f"{CLOUD_API}/client/users/me",
        headers={
            "Authorization": f"{uid} {token}",
            "Content-Type": "application/json",
            "User-Agent": f"Zed/{os.environ.get('ZED_VERSION', '1.6.3')}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            plan = data.get("plan", {})
            plan_v3 = plan.get("plan_v3", "?")
            if isinstance(plan_v3, dict):
                plan_v3 = plan_v3.get("known", "?")

            user = data.get("user", {})
            orgs = data.get("organizations", [])
            default_org = data.get("default_organization_id", {})
            if isinstance(default_org, dict):
                default_org = default_org.get("0")

            logger.info(f"  GitHub: {user.get('github_login', '?')}")
            logger.info(f"  Plan: {plan_v3}")
            logger.info(f"  Trial started: {plan.get('trial_started_at', 'N/A')}")
            logger.info(f"  Account too young: {plan.get('is_account_too_young', '?')}")
            logger.info(f"  Overdue invoices: {plan.get('has_overdue_invoices', '?')}")
            logger.info(f"  组织数: {len(orgs)}")
            logger.info(f"  默认组织: {default_org}")

            return data, default_org
    except urllib.error.HTTPError as e:
        logger.error(f"  HTTP {e.code}: {e.read().decode()[:200]}")
        return None, None
    except Exception as e:
        logger.error(f"  请求失败: {e}")
        return None, None


def test_llm_token(uid, token, org_id):
    """POST /client/llm_tokens"""
    import urllib.request

    body = json.dumps({"organization_id": org_id}).encode()
    req = urllib.request.Request(
        f"{CLOUD_API}/client/llm_tokens",
        data=body,
        headers={
            "Authorization": f"{uid} {token}",
            "Content-Type": "application/json",
            "User-Agent": "Zed/1.6.3",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            token_val = data.get("token", {})
            if isinstance(token_val, dict):
                token_val = token_val.get("0", str(token_val))
            logger.info(f"  LLM Token: {str(token_val)[:20]}...")
            logger.info(f"  响应头: x-zed-expired-token={resp.headers.get('x-zed-expired-token', 'N/A')}")
            return token_val
    except urllib.error.HTTPError as e:
        logger.error(f"  HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except Exception as e:
        logger.error(f"  请求失败: {e}")
        return None


def test_models(llm_token):
    """GET /models"""
    import urllib.request

    req = urllib.request.Request(
        f"{CLOUD_API}/models",
        headers={
            "Authorization": f"Bearer {llm_token}",
            "x-zed-client-supports-x-ai": "true",
            "User-Agent": "Zed/1.6.3",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
            models = data.get("models", [])
            logger.info(f"  模型数: {len(models)}")
            for m in models[:8]:
                mid = m.get("id", {})
                if isinstance(mid, dict): mid = mid.get("0", "?")
                prov = m.get("provider", "?")
                name = m.get("display_name", mid)
                tools = "T" if m.get("supports_tools") else "."
                think = "T" if m.get("supports_thinking") else "."
                logger.info(f"    [{prov}] {name} ({mid}) [工具={tools},思考={think}]")
            if len(models) > 8:
                logger.info(f"    ... 还有 {len(models)-8} 个")
            return data
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:300]
        logger.error(f"  HTTP {e.code}: {body}")
        return None


def test_completion(llm_token):
    """POST /completions — 发一条最简单的消息"""
    import urllib.request

    provider_request = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 50,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "Hi"}]}],
        "stream": True,
    }
    body = json.dumps({
        "provider": "anthropic",
        "model": "claude-sonnet-4-20250514",
        "provider_request": provider_request,
    }).encode()

    req = urllib.request.Request(
        f"{CLOUD_API}/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {llm_token}",
            "Content-Type": "application/json",
            "User-Agent": "Zed/1.6.3",
            "x-zed-client-supports-status-messages": "true",
            "x-zed-client-supports-stream-ended-request-completion-status": "true",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            logger.info(f"  状态: {resp.status}")
            logger.info(f"  头: x-zed-server-supports-status-messages={resp.headers.get('x-zed-server-supports-status-messages', 'N/A')}")
            raw = resp.read().decode()
            lines = [l for l in raw.split("\n") if l.strip()]
            logger.info(f"  收到 {len(lines)} 行事件:")
            for line in lines[:15]:
                try:
                    evt = json.loads(line)
                    if "Status" in evt:
                        logger.info(f"    Status: {json.dumps(evt['Status'])[:80]}")
                    elif "Event" in evt:
                        e = evt["Event"]
                        if isinstance(e, dict):
                            logger.info(f"    Event: {json.dumps(e)[:120]}")
                        else:
                            logger.info(f"    Event: {str(e)[:120]}")
                except Exception:
                    logger.info(f"    RAW: {line[:120]}")
            if len(lines) > 15:
                logger.info(f"    ... 还有 {len(lines)-15} 行")
            return raw
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        logger.error(f"  HTTP {e.code}: {body}")
        return None


# ============================================================
# 主流程
# ============================================================

def main():
    logger.info("=" * 60)
    logger.info("Zed 真实 API 测试")
    logger.info(f"时间: {datetime.now().isoformat()}")
    logger.info("=" * 60)

    # Step 1: 找凭证
    logger.info("\n[1/5] 查找本地 Zed 凭证...")
    creds_list = find_zed_credentials()

    if not creds_list:
        logger.info("  没有找到 Zed 凭证。")
        logger.info("")
        logger.info("请选择以下方式之一提供凭证:")
        logger.info("")
        logger.info("  A. 在本机（装有 Zed 并登录过）运行此脚本")
        logger.info("")
        logger.info("  B. 从 Zed 的凭证文件中复制内容:")
        logger.info("      macOS: 打开钥匙串访问 → 搜索 zed.dev")
        logger.info("      Linux: cat ~/.config/zed/development_credentials")
        logger.info("     然后设置环境变量运行:")
        logger.info("       export ZED_USER_ID=你的ID")
        logger.info("       export ZED_ACCESS_TOKEN=你的token")
        logger.info(f"       python3 {__file__}")
        logger.info("")
        return

    for source, uid, token in creds_list:
        logger.info(f"  来源: {source}")
        logger.info(f"  User ID: {uid}")
        logger.info(f"  Token: {token[:20]}...")

        # Step 2: 获取用户信息
        logger.info(f"\n[2/5] GET /client/users/me (来源: {source})")
        user_data, org_id = test_get_user(uid, token)

        if user_data is None:
            logger.warning(f"  → 此凭证无效，尝试下一个")
            continue

        # Step 3: 获取 LLM Token
        logger.info(f"\n[3/5] POST /client/llm_tokens")
        if not org_id:
            orgs = user_data.get("organizations", [])
            if orgs:
                org_id = orgs[0].get("id", {}).get("0")
                logger.info(f"  使用第一个组织: {org_id}")
            else:
                logger.error("  没有可用的组织")
                continue

        llm_token = test_llm_token(uid, token, org_id)
        if not llm_token:
            logger.warning("  → 无法获取 LLM Token")
            continue

        # Step 4: 模型列表
        logger.info(f"\n[4/5] GET /models")
        models_data = test_models(llm_token)

        if models_data is None:
            continue

        # Step 5: Completion 测试
        logger.info(f"\n[5/5] POST /completions (流式)")
        logger.info("  (发送一条 'Hi' 给 claude-sonnet-4-20250514)")
        test_completion(llm_token)

        # 完成
        logger.info(f"\n{'='*60}")
        logger.info(f"✅ 测试完成 (来源: {source})")
        logger.info(f"{'='*60}")
        return

    logger.error("\n❌ 所有凭证都无效")


if __name__ == "__main__":
    main()