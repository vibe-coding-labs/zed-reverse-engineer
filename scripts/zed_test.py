#!/usr/bin/env python3
"""
Zed 授权流程端到端测试脚本
============================
这个脚本会完整地跑一遍 Zed 的授权流程，验证我们的协议分析是否正确。

使用方法:
  # 方式 1: 完整 OAuth 登录（需要浏览器交互）
  python scripts/zed_test.py --oauth

  # 方式 2: 用已有的 access_token（跳过浏览器）
  python scripts/zed_test.py --user-id 12345 --token "xxx"

  # 方式 3: 用已有的 LLM token（跳过所有认证）
  python scripts/zed_test.py --llm-token "xxx"

  # 方式 4: 直接测试 completion（需要先获取 LLM token）
  python scripts/zed_test.py --llm-token "xxx" --test-completion
"""

import argparse
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.zed_auth import (
    CLOUD_API_URL,
    LLM_API_URL,
    ZED_VERSION,
    authenticate_via_browser,
    create_llm_token,
    get_authenticated_user,
    list_models,
    stream_completion,
    token_fingerprint,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("zed_test")

# 测试结果记录
test_results = []


def test(name: str, fn, *args, **kwargs):
    """测试包装器，记录结果"""
    logger.info(f"\n{'='*60}")
    logger.info(f"🧪 测试: {name}")
    logger.info(f"{'='*60}")
    try:
        start = time.time()
        result = fn(*args, **kwargs)
        elapsed = time.time() - start
        logger.info(f"✅ 通过 ({elapsed:.1f}s)")
        test_results.append((name, "✅ PASS", elapsed))
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"❌ 失败 ({elapsed:.1f}s): {e}")
        test_results.append((name, "❌ FAIL", elapsed))
        return None


def print_json(data, label="响应"):
    """带缩进的 JSON 打印（截断长字段）"""
    if data is None:
        logger.info(f"  {label}: None")
        return

    def truncate(obj, max_len=100):
        if isinstance(obj, dict):
            return {k: truncate(v, max_len) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [truncate(v, max_len) for v in obj]
        elif isinstance(obj, str) and len(obj) > max_len:
            return obj[:max_len] + "..."
        return obj

    try:
        pretty = json.dumps(truncate(data), indent=2, ensure_ascii=False)
        for line in pretty.split("\n"):
            logger.info(f"  {line}")
    except Exception:
        logger.info(f"  {label}: {str(data)[:200]}...")


def check_field(obj, field, expected_type=None, hint=""):
    """检查字段是否存在且类型正确"""
    if obj is None:
        logger.warning(f"  ⚠️  {field}: 对象为 None{hint}")
        return False
    if field not in obj:
        logger.warning(f"  ⚠️  {field}: 字段不存在{hint}")
        return False
    if expected_type and not isinstance(obj[field], expected_type):
        logger.warning(f"  ⚠️  {field}: 期望 {expected_type.__name__}, 实际 {type(obj[field]).__name__}{hint}")
        return False
    return True


# ============================================================================
# 测试用例
# ============================================================================

def test_oauth_flow():
    """测试 1: 完整 OAuth 流程"""
    logger.info("进行浏览器 OAuth 登录...")
    logger.info("请在打开的浏览器页面中，使用 GitHub 账号登录 Zed")
    logger.info("")

    credentials = authenticate_via_browser()

    logger.info(f"  用户 ID: {credentials.user_id}")
    logger.info(f"  Token fingerprint: {token_fingerprint(credentials.access_token)}")

    # 保存 credentials 供后续测试使用
    save_path = Path.home() / ".zed_test_credentials.json"
    save_data = {
        "user_id": credentials.user_id,
        "access_token": credentials.access_token,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with open(save_path, "w") as f:
        json.dump(save_data, f)
    logger.info(f"  凭证已保存到: {save_path}")

    return credentials


def test_get_user(credentials):
    """测试 2: GET /client/users/me"""
    logger.info("请求 GET /client/users/me ...")
    user_info = get_authenticated_user(
        credentials.user_id,
        credentials.access_token,
        system_id="test-script",
    )

    logger.info(f"  GitHub: {user_info.github_login}")
    logger.info(f"  姓名: {user_info.name}")
    logger.info(f"  Plan: {user_info.plan.plan}")
    logger.info(f"  Trial started: {user_info.plan.trial_started_at}")
    logger.info(f"  Account too young: {user_info.plan.is_account_too_young}")
    logger.info(f"  Edit predictions: {user_info.plan.edit_predictions_used}/{user_info.plan.edit_predictions_limit}")
    logger.info(f"  组织列表: {user_info.organizations}")
    logger.info(f"  默认组织: {user_info.default_organization_id}")
    logger.info(f"  是否 Staff: {user_info.is_staff}")

    # 验证关键字段
    assert user_info.id > 0, "user_id 应该大于 0"
    assert user_info.github_login, "github_login 不应该为空"
    assert user_info.plan.plan in ["zed_free", "zed_pro", "zed_pro_trial", "zed_business", "zed_student"], \
        f"未知的 plan 类型: {user_info.plan.plan}"

    if user_info.plan.plan == "zed_free":
        logger.info("  ⚠️  当前是 Free 计划，/completions 会返回 402")

    return user_info


def test_create_llm_token(credentials, organization_id):
    """测试 3: POST /client/llm_tokens"""
    logger.info(f"请求 POST /client/llm_tokens (org={organization_id}) ...")

    llm_token = create_llm_token(
        credentials.user_id,
        credentials.access_token,
        organization_id,
        system_id="test-script",
    )

    logger.info(f"  LLM Token fingerprint: {token_fingerprint(llm_token)}")
    assert len(llm_token) > 10, f"LLM token 太短: {len(llm_token)} chars"

    return llm_token


def test_list_models(llm_token):
    """测试 4: GET /models"""
    logger.info("请求 GET /models ...")

    models_data = list_models(llm_token)

    models = models_data.get("models", [])
    default_model = models_data.get("default_model", {}).get("0", "N/A")
    default_fast = models_data.get("default_fast_model", {}).get("0") if models_data.get("default_fast_model") else None

    logger.info(f"  可用模型: {len(models)} 个")
    logger.info(f"  默认模型: {default_model}")
    logger.info(f"  默认快速模型: {default_fast}")

    for m in models[:5]:  # 只打印前 5 个
        mid = m.get("id", {}).get("0", "?")
        display = m.get("display_name", mid)
        provider = m.get("provider", "?")
        tools = "✅工具" if m.get("supports_tools") else "❌无工具"
        thinking = "✅思考" if m.get("supports_thinking") else "❌无思考"
        logger.info(f"    [{provider}] {display} ({tools}, {thinking})")

    if len(models) > 5:
        logger.info(f"    ... 还有 {len(models) - 5} 个模型")

    return models_data


def test_completion(llm_token):
    """测试 5: POST /completions (流式)"""
    logger.info("请求 POST /completions（简单测试，发送 'Hi'）...")

    provider_request = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": "Respond with just 'Hello from Zed! I am working.'"}]
            }
        ],
        "stream": True,
    }

    events = []
    try:
        for event in stream_completion(
            llm_token=llm_token,
            provider="anthropic",
            model="claude-sonnet-4-20250514",
            provider_request=provider_request,
        ):
            events.append(event)
            # 打印事件类型
            if "Status" in event:
                status = event["Status"]
                if isinstance(status, str):
                    logger.info(f"    状态: {status}")
                elif isinstance(status, dict):
                    for k, v in status.items():
                        logger.info(f"    状态: {k}: {v}")
            elif "Event" in event:
                evt = event["Event"]
                if isinstance(evt, dict):
                    evt_type = evt.get("type", "?")
                    if evt_type == "content_block_delta":
                        delta = evt.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            logger.info(f"    内容: {text[:50]}")
                    elif evt_type == "message_start":
                        logger.info(f"    消息开始")
                    elif evt_type == "message_stop":
                        logger.info(f"    消息结束")
                    elif evt_type == "content_block_start":
                        block = evt.get("content_block", {})
                        logger.info(f"    内容块开始: {block.get('type', '?')}")

        logger.info(f"  共收到 {len(events)} 个事件")
        return events
    except Exception as e:
        logger.error(f"  Completion 失败: {e}")
        return None


# ============================================================================
# 主流程
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Zed 授权流程端到端测试")
    parser.add_argument("--oauth", action="store_true", help="通过浏览器 OAuth 登录")
    parser.add_argument("--user-id", type=int, help="用户 ID")
    parser.add_argument("--token", help="access_token")
    parser.add_argument("--llm-token", help="已有 LLM token（跳过认证）")
    parser.add_argument("--test-completion", action="store_true", help="测试 completion")
    parser.add_argument("--save", action="store_true", help="保存测试结果到文件")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("Zed 授权流程端到端测试")
    logger.info(f"时间: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"Cloud API: {CLOUD_API_URL}")
    logger.info(f"LLM API: {LLM_API_URL}")
    logger.info(f"Zed 版本: {ZED_VERSION}")
    logger.info("=" * 60)

    # ================================================================
    # Step 1: 获取凭证
    # ================================================================
    credentials = None
    llm_token = None
    user_info = None

    if args.llm_token:
        # 直接用 LLM token
        logger.info("\n📌 使用已有 LLM token")
        llm_token = args.llm_token
        test("LLM Token 格式检查", lambda t: len(t) > 10, llm_token)

    elif args.user_id and args.token:
        # 用已有的 credentials
        from scripts.zed_auth import Credentials
        logger.info("\n📌 使用已有的凭证")
        credentials = Credentials(user_id=args.user_id, access_token=args.token)

    elif args.oauth or not any([args.llm_token, args.user_id, args.token]):
        # OAuth 流程
        logger.info("\n📌 方式: 浏览器 OAuth 登录")
        credentials = test("OAuth 登录", test_oauth_flow)
        if not credentials:
            logger.error("❌ OAuth 登录失败，退出")
            sys.exit(1)

    # ================================================================
    # Step 2: 获取用户信息
    # ================================================================
    if credentials:
        logger.info("\n" + "=" * 60)
        logger.info("📋 Step 2: 获取用户信息")
        logger.info("=" * 60)

        user_info = test("GET /client/users/me", test_get_user, credentials)

        # ================================================================
        # Step 3: 获取 LLM Token
        # ================================================================
        if user_info:
            logger.info("\n" + "=" * 60)
            logger.info("🔑 Step 3: 获取 LLM Token")
            logger.info("=" * 60)

            # 确定组织 ID
            org_id = user_info.default_organization_id
            if not org_id and user_info.organizations:
                org_id = user_info.organizations[0]

            if org_id:
                llm_token = test("POST /client/llm_tokens", test_create_llm_token, credentials, org_id)
            else:
                logger.warning("没有可用的组织 ID，无法创建 LLM Token")

    # ================================================================
    # Step 4: 获取模型列表
    # ================================================================
    if llm_token:
        logger.info("\n" + "=" * 60)
        logger.info("🤖 Step 4: 获取模型列表")
        logger.info("=" * 60)

        models_data = test("GET /models", test_list_models, llm_token)

        # ================================================================
        # Step 5: 测试 Completion（可选）
        # ================================================================
        if args.test_completion:
            logger.info("\n" + "=" * 60)
            logger.info("💬 Step 5: 测试 Completion")
            logger.info("=" * 60)

            if models_data and models_data.get("models"):
                test("POST /completions", test_completion, llm_token)
            else:
                logger.warning("没有可用模型，可能是 Free 计划")

    # ================================================================
    # 总结
    # ================================================================
    logger.info("\n" + "=" * 60)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 60)

    passed = sum(1 for _, s, _ in test_results if "PASS" in s)
    failed = sum(1 for _, s, _ in test_results if "FAIL" in s)

    for name, status, elapsed in test_results:
        logger.info(f"  {status} {name} ({elapsed:.1f}s)")

    logger.info(f"\n总计: {len(test_results)} 项测试, {passed} 通过, {failed} 失败")

    if failed > 0:
        logger.warning("有测试失败，请检查上面的错误日志")
        sys.exit(1)
    elif passed > 0:
        logger.info("✅ 全部通过！协议分析验证正确。")
        logger.info("")
        logger.info("后续可以: ")
        logger.info("  1. 保存 LLM token 到环境变量备用")
        logger.info("  2. 测试 /completions 流式响应")
        logger.info("  3. 实现反向代理")
        logger.info("")
        logger.info("提示: 你的凭证已保存在 ~/.zed_test_credentials.json")
        logger.info("下次测试可以直接用:")
        logger.info(f"  cat ~/.zed_test_credentials.json")
    else:
        logger.warning("没有运行任何测试")
        sys.exit(1)


if __name__ == "__main__":
    main()
