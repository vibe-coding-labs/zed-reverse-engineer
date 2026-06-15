# 反向代理方案设计

## 目标

将 Zed 的 AI 能力反向代理给 Claude Code、Codex 或其他终端工具使用。核心思路是拦截 Zed Cloud API 的 LLM 请求，将其路由到我们自己的代理服务，实现对 AI 调用的统一管理和路由。

---

## 一、方案对比

### 方案 A: HTTP 代理模式（推荐）

在 Zed 和 cloud.zed.dev 之间插入 HTTP 代理，劫持 `/completions` 和 `/models` 请求。

```
┌──────────┐     ┌──────────────┐     ┌──────────────┐
│ Claude   │     │  反向代理     │     │ cloud.zed.dev│
│ Code/Zed │────▶│ (mitmproxy/  │────▶│ (或绕过)     │
│          │     │  nginx/定制)  │     │              │
└──────────┘     └──────┬───────┘     └──────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │  目标 API    │
                 │ (Claude/     │
                 │  OpenAI/自建)│
                 └──────────────┘
```

**优点**: 零侵入，无需修改 Zed 源码

**缺点**: 需要处理认证劫持，有中间人复杂度

### 方案 B: 环境变量覆盖 + 自建 LLM 服务

利用 `ZED_SERVER_URL` 环境变量将 Zed 指向自建服务。

```
ZED_SERVER_URL=http://localhost:3000  zed

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

**优点**: 配置简单，完全掌控流量

**缺点**: 需要实现完整的 API 模拟

### 方案 C: ACP 桥接模式

利用 Zed 的 ACP (Agent Communication Protocol) 协议桥接外部 Agent。

```
┌──────────┐   ACP (stdin/stdout)   ┌──────────────┐
│ Zed      │◀──────────────────────▶│ ACP Bridge   │
│          │                        │              │
└──────────┘                        │ JSON-RPC 2.0 │
                                    │  ↔ 目标 API  │
                                    └──────────────┘
```

**优点**: 协议标准，可扩展

**缺点**: ACP 协议尚在演进，文档少

---

## 二、推荐方案 — 方案 B 详解

### 2.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                   反向代理服务 (端口 3000)                      │
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ Auth       │  │ Model      │  │ Completion              │ │
│  │ Handler    │  │ Handler    │  │ Handler                 │ │
│  │            │  │            │  │                         │ │
│  │ /client/   │  │ GET /models│  │ POST /completions       │ │
│  │ llm_tokens │  │            │  │                         │ │
│  │ /users/me  │  │            │  │ → 路由到目标 LLM API    │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 需要实现的端点

#### GET /client/users/me

```json
// 请求
GET /client/users/me
Authorization: 1 fake_token

// 响应 200
{
  "id": 1,
  "email": "user@example.com",
  "name": "Proxy User"
}
```

#### POST /client/llm_tokens

```json
// 请求
POST /client/llm_tokens
Authorization: 1 fake_token
Content-Type: application/json

{
  "organization_id": "org-1"
}

// 响应 200
{
  "token": {
    "0": "zed_llm_proxy_token_xxxx"
  }
}
```

#### GET /models

```json
// 请求
GET /models
Authorization: Bearer zed_llm_proxy_token_xxxx
x-zed-client-supports-x-ai: true

// 响应 200
{
  "models": [
    {
      "provider": "anthropic",
      "id": {"0": "claude-sonnet-4-20250514"},
      "display_name": "Claude Sonnet 4",
      "is_latest": true,
      "max_token_count": 200000,
      "max_output_tokens": 8192,
      "supports_tools": true,
      "supports_images": true,
      "supports_thinking": true,
      "supports_disabling_thinking": true,
      "supports_fast_mode": false,
      "supported_effort_levels": [
        {"name": {"0": "Low"}, "value": {"0": "low"}, "is_default": false},
        {"name": {"0": "Medium"}, "value": {"0": "medium"}, "is_default": true},
        {"name": {"0": "High"}, "value": {"0": "high"}, "is_default": false}
      ],
      "supports_streaming_tools": true,
      "supports_parallel_tool_calls": false
    }
  ],
  "default_model": {"0": "claude-sonnet-4-20250514"},
  "default_fast_model": null,
  "recommended_models": [{"0": "claude-sonnet-4-20250514"}]
}
```

#### POST /completions — 核心端点

##### 入站请求 (来自 Zed)

```json
{
  "thread_id": "uuid",
  "prompt_id": "uuid",
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

##### 处理逻辑

1. 解析 `provider` 和 `model` 字段
2. 提取 `provider_request` 中的消息和工具
3. 转换为目标 API 格式（如 Anthropic Messages API 或 OpenAI Chat API）
4. 流式转发响应

##### 流式响应格式

```json
// 行 1 (先发状态)
{"Status":{"Queued":{"position":0}}}

// 行 2
{"Status":"Started"}

// 行 3-N (上游事件)
{"Event":{...}}
{"Event":{...}}

// 最后一行
{"Status":"StreamEnded"}
```

### 2.3 配置设计

```yaml
# proxy-config.yaml
server:
  port: 3000
  host: "0.0.0.0"

upstream:
  # 目标 LLM API
  type: "anthropic"     # anthropic | openai | custom
  api_key: "${API_KEY}"
  base_url: "https://api.anthropic.com"
  
  # 或使用 OpenAI 兼容 API
  # type: "openai"
  # api_key: "${OPENAI_API_KEY}"
  # base_url: "https://api.openai.com/v1"

models:
  # 暴露给 Zed 的模型列表
  - provider: "anthropic"
    id: "claude-sonnet-4-20250514"
    display_name: "Claude Sonnet 4"
    max_token_count: 200000
    max_output_tokens: 8192
    supports_tools: true
    supports_images: true
    supports_thinking: true
    is_latest: true
  - provider: "open_ai"
    id: "gpt-4o"
    display_name: "GPT-4o"
    max_token_count: 128000
    max_output_tokens: 4096
    supports_tools: true
    supports_images: true
    supports_thinking: false
    is_latest: false
```

---

## 三、使用方式

### 3.1 启动代理

```bash
export ZED_SERVER_URL=http://localhost:3000
zed
```

或者通过配置文件设置 `server_url: "http://localhost:3000"`。

### 3.2 配合 Claude Code

```bash
# 在 Claude Code 中配置使用代理
# Claude Code 通过环境变量支持自定义 API 端点
export ANTHROPIC_BASE_URL=http://localhost:3000/v1
claude
```

### 3.3 配合 Codex

```bash
# 通过 OpenAI 兼容 API 的方式对接
export OPENAI_BASE_URL=http://localhost:3000/v1
codex
```

---

## 四、注意事项

### 4.1 credential 存储

Zed 的凭证存储在本地，需要确保代理服务有有效的凭证或模拟凭证。最简单的方式是在开发模式启动：

```bash
# 开发模式
export ZED_SERVER_URL=http://localhost:3000
zed --dev
```

### 4.2 版本兼容

- 检查 `x-zed-version` 头，确保响应格式兼容
- 留意 `MINIMUM_REQUIRED_VERSION_HEADER_NAME` 响应头

### 4.3 限流与配额

- Zed 客户端内置了 `RateLimiter` (并发限制为 4)
- 需要处理 402 Payment Required 响应
- 注意 `x-zed-edit-predictions-usage-limit` 和 `x-zed-edit-predictions-usage-amount` 头

### 4.4 协议差异处理

不同 provider 的消息格式不同：
- **Anthropic**: Messages API (role: user/assistant, content blocks)
- **OpenAI**: Chat Completions API (role: system/user/assistant, content string)
- **Google**: Gemini API (contents structure)
- **xAI**: OpenAI 兼容格式

代理需要正确处理格式转换。

### 4.5 图像处理

Zed 发送图片时会将图片转换为 base64 PNG（最大 5MB），并使用 `LanguageModelImage` 结构体。需要确保代理正确处理图片 MIME 类型。

---

## 五、实现步骤

1. **搭建基础 HTTP 服务** — 监听 3000 端口，处理 /completions、/models、/client/*
2. **实现认证模拟** — 模拟 /client/users/me 和 /client/llm_tokens
3. **模型列表** — 返回自定义模型列表
4. **Completion 转发** — 解析 provider_request，转发到目标 API，流式返回
5. **配置与部署** — 支持配置文件和环境变量
6. **测试验证** — 使用 `ZED_SERVER_URL` 指向代理，验证完整流程
