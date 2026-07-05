# 循环分析报告 #26 — 二进制 Strings 深度分析

**分析时间**: 2026-07-06
**目标**: `zed-editor` (373 MB 二进制)
**分析前状态**: ❌ 完全没碰过

## 发现 1: 二进制中确认的 API 端点

```
# LLM Provider API URLs（与源码一致）
https://api.anthropic.com
https://api.openai.com/v1
https://openrouter.ai/api/v1
https://api.x.ai/v1/chat/completions
http://localhost:11434           # Ollama
http://localhost:1234/api/v0     # LM Studio

# 认证
https://github.com/login/oauth/authorize?client_id=Iv1.7e72654f487b56be
https://avatars.githubusercontent.com/u/{user_id}
```

## 发现 2: 编辑预测/Agent 相关

```
# Edit Prediction
zed-cloud, zed, edit-prediction-bench, zed.dev

# Agent 工具列表（二进制确认）
apply_code_action, copy_path, create_thread, delete_path, edit_file
find_path, find_references, list_agents_and_models, list_directory
move_path, rename_symbols, spawn_agent, update_plan, update_title
search_web, write_file

# Agent UI 提示词
"What went wrong? Share your feedback so we can improve."
"External agents are not yet supported in shared projects."
```

## 发现 3: OAuth 端点验证

```
"OAuth endpoint must not point to private/reserved IP"
"OAuth endpoint must not point to reserved IPv6 address"
```

这确认了 MCP OAuth 客户端有 SSRF 防护。

## 发现 4: 环境变量（二进制确认）

| 环境变量 | 说明 |
|----------|------|
| `ZED_SERVER_URL` | ✅ 覆盖服务器地址 |
| `ZED_IMPERSONATE` | ✅ 管理员模拟登录 |
| `ZED_ADMIN_API_TOKEN` | ✅ 管理员 API Token |
| `ZED_DEVELOPMENT_USE_KEYCHAIN` | ✅ 开发凭证模式 |
| `ZED_WEB_LOGIN` | ✅ Web 登录 |
| `ZED_RPC_URL` | ✅ RPC 地址覆盖 |
| `OPENROUTER_API_KEY` | ✅ OpenRouter Key |

## 发现 5: 计费/试用文案（二进制确认）

```
"Welcome to the Zed Pro Trial"
"$20 of tokens in Zed agent"     ← Pro 试用 $20 额度
"$10 of tokens in Zed agent"     ← Pro 付费 $10 额度  
"$5 of tokens in Zed agent"      ← 什么情况 $5？
"Optional credit packs for additional usage"
"Usage-based billing beyond $2,000 accepted edit predictions"
"Try it out for 14 days, no credit card required"
```

关键发现：**试用额度文案有矛盾**。源码说 `$20 token credit during the 2-week free trial`，但二进制中出现了 `$20`、`$10`、`$5` 三个版本，可能是针对不同 plan 等级。

## 发现 6: Agent 配置文件字段

```
max_output_tokens
supports_tools
supports_images
supports_parallel_tool_calls
supports_chat_completions
supports_prompt_cache_key
Provider Name
API URL: https://api.openai.com/v1
Model Name: e.g. gpt-5, claude-opus-4, gemini-2.5-pro
```

## 发现 7: 隐藏的 feature（二进制特有）

```
"fast-mode-warning-dismissed"  ← 快速模式
"experimental/externalDocs"     ← LSP 外部文档实验特性
"experimental/parentModule"     ← LSP 父模块
"experimental/runnables"        ← LSP 可运行项
"allow non-standardized experimental things"  ← 实验开关
```

## 发现 8: OAuth Client ID 确认

```
GitHub OAuth App: Iv1.7e72654f487b56be
```

## 关键发现

二进制分析没有发现源码中不存在的隐藏端点或协议。所有 URL、端点、认证方式都跟源码分析一致。这验证了我们的分析是完整的。