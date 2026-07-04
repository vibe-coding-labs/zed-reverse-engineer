---
title: 反向代理方案设计
description: 将 Zed 的 AI 能力反向代理给 Claude Code、Codex 等工具的方案设计
---

# 反向代理方案设计

## 目标

将 Zed 的 AI 能力反向代理给 Claude Code、Codex 或其他终端工具使用。核心思路是拦截 Zed Cloud API 的 LLM 请求，将其路由到我们自己的代理服务，实现对 AI 调用的统一管理和路由。

---

## 一、方案对比

| 方案 | 原理 | 优点 | 缺点 |
|------|------|------|------|
| **A: HTTP 代理** | 在 Zed 和 cloud.zed.dev 之间插入 HTTP 代理 | 零侵入 | 中间人复杂度 |
| **B: ZED_SERVER_URL 劫持** | 环境变量覆盖服务器地址 | 配置简单，完全掌控 | 需实现完整 API 模拟 |
| **C: ACP 桥接** | 利用 ACP 协议桥接外部 Agent | 协议标准 | 文档少，复杂度高 |

### 推荐方案 B: ZED_SERVER_URL 劫持

```
ZED_SERVER_URL=http://localhost:3000 zed

┌──────────┐     ┌──────────────────┐
│ Zed      │────▶│ 本地反向代理服务   │
│          │     │ 监听 :3000        │
└──────────┘     └────────┬─────────┘
                          │
                          ├──▶ /completions → 目标 API
                          ├──▶ /models → 自定义模型列表
                          ├──▶ /client/llm_tokens → 模拟响应
                          └──▶ /client/users/me → 模拟响应
```

---

## 二、需要实现的端点

### GET /client/users/me

```json
{
  "user": { "id": 1, "github_login": "proxy-user", ... },
  "organizations": [{ "id": {"0": "org-1"}, "name": "Personal", "is_personal": true }],
  "default_organization_id": {"0": "org-1"},
  "plan": {
    "plan_v3": {"known": "zed_pro"},
    "usage": { "edit_predictions": { "used": 0, "limit": "unlimited" } }
  }
}
```

### POST /client/llm_tokens

```json
{
  "token": {"0": "zed_llm_proxy_token_xxxx"}
}
```

### GET /models

```json
{
  "models": [{
    "provider": "anthropic",
    "id": {"0": "claude-sonnet-4-20250514"},
    "display_name": "Claude Sonnet 4",
    "max_token_count": 200000,
    "max_output_tokens": 8192,
    "supports_tools": true,
    "supports_images": true,
    "supports_thinking": true
  }],
  "default_model": {"0": "claude-sonnet-4-20250514"},
  "recommended_models": [{"0": "claude-sonnet-4-20250514"}]
}
```

### POST /completions（核心端点）

**入站请求（来自 Zed）:**
```json
{
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "provider_request": {
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 8192,
    "messages": [...],
    "tools": [...],
    "stream": true
  }
}
```

**流式响应格式:**
```json
{"Status":{"Queued":{"position":0}}}
{"Status":"Started"}
{"Event":{...}}  // 上游 provider 原始事件
{"Status":"StreamEnded"}
```

---

## 三、Mock Server 实现

项目提供了完整的 Mock Server (`scripts/zed_mock_server.py`):

```bash
# 启动 Mock Server
python3 scripts/zed_mock_server.py --port 3000 --plan zed_pro

# 另一个终端启动 Zed
ZED_DEVELOPMENT_USE_KEYCHAIN=true \
ZED_SERVER_URL=http://localhost:3000 \
zed
```

---

## 四、配置设计

```yaml
# proxy-config.yaml
server:
  port: 3000
  host: "0.0.0.0"

upstream:
  type: "anthropic"       # anthropic | openai | custom
  api_key: "${API_KEY}"
  base_url: "https://api.anthropic.com"

models:
  - provider: "anthropic"
    id: "claude-sonnet-4-20250514"
    display_name: "Claude Sonnet 4"
    max_token_count: 200000
    max_output_tokens: 8192
    supports_tools: true
    supports_images: true
    supports_thinking: true
    is_latest: true
```

---

## 五、注意事项

1. **凭证存储**: Zed 凭证存储在系统 keychain，开发模式可用 `development_credentials` 文件绕过
2. **版本兼容**: 检查 `x-zed-version` 头，确保响应格式兼容
3. **限流**: Zed 客户端内置了 `RateLimiter`（并发限制为 4）
4. **协议差异**: 不同 provider 的消息格式不同，代理需要正确处理格式转换

---

## 参考

- `scripts/zed_mock_server.py` — Mock Server 实现
- `scripts/zed_auth.py` — Python 授权实现
- `crates/http_client/src/http_client.rs` — URL 构建逻辑