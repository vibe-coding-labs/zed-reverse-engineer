# Zed AI 通信协议分析

## 概述

Zed 编辑器提供了两种 AI 通信模式：
1. **Zed Cloud 代理模式** — 通过 `zed.dev` / `cloud.zed.dev` 中转请求到上游 LLM 提供商
2. **直连模式** — 用户配置自己的 API Key，直接连接 Anthropic / OpenAI / Google / xAI
3. **ACP (Agent Communication Protocol)** — 用于 Zed 编辑器与外部 Agent 进程之间的通信

本文档主要关注第一种模式，这是反向代理的核心目标。

---

## 一、架构总览

```
┌─────────────────────────────────────────────────┐
│                  Zed 编辑器                       │
│                                                   │
│  ┌──────────┐   ┌────────────────────────┐       │
│  │ Agent UI  │   │ LanguageModelRegistry   │       │
│  └────┬─────┘   └──────────┬─────────────┘       │
│       │                    │                      │
│  ┌────▼────────────────────▼─────────────┐       │
│  │      CloudLanguageModelProvider        │       │
│  │      (provider_id = "zed.dev")         │       │
│  └────────────────┬──────────────────────┘       │
│                   │                               │
└───────────────────│───────────────────────────────┘
                    │
                    │ HTTP POST /completions
                    │ Authorization: Bearer {llm_token}
                    │ x-zed-version: 1.6.3
                    │ x-zed-client-supports-status-messages: true
                    │
                    ▼
          ┌─────────────────────┐
          │   cloud.zed.dev     │  (或 llm-staging.zed.dev)
          │   LLM Proxy Service │
          └──────────┬──────────┘
                     │
          ┌──────────┴──────────┐
          │   Upstream Provider │
          │  (Anthropic/OpenAI/ │
          │   Google/xAI)       │
          └─────────────────────┘
```

---

## 二、核心通信协议

### 2.1 LLM Completion 请求

**端点**: `POST https://cloud.zed.dev/completions`

**认证**: `Authorization: Bearer {llm_token}`

LLM Token 通过以下方式获取：
1. 用户登录 Zed (GitHub OAuth)
2. 客户端调用 `POST /client/llm_tokens` 获取 LLM Token
3. LLM Token 被缓存，过期时通过 `x-zed-expired-token` 或 `x-zed-outdated-token` 头通知刷新

**请求体结构** (`CompletionBody`):

```json
{
  "thread_id": "uuid-string",
  "prompt_id": "uuid-string",
  "provider": "anthropic|open_ai|google|x_ai",
  "model": "claude-sonnet-4-20250514",
  "provider_request": { /* 上游 provider 的原始请求体 */ }
}
```

`provider_request` 字段直接透传上游 provider 格式的请求体。对于 Anthropic 这就是 Anthropic Messages API 格式，对于 OpenAI 就是 Chat Completions 格式。

### 2.2 关键 HTTP 头

| 请求头 | 说明 |
|--------|------|
| `Authorization: Bearer {token}` | LLM 认证 Token |
| `x-zed-version` | 客户端版本号 |
| `x-zed-client-supports-status-messages` | 客户端支持状态消息 |
| `x-zed-client-supports-stream-ended-request-completion-status` | 支持 StreamEnded 状态 |
| `x-zed-client-supports-x-ai` | 支持 xAI 模型 |

| 响应头 | 说明 |
|--------|------|
| `x-zed-expired-token` | Token 过期，需要刷新 |
| `x-zed-outdated-token` | Token 结构过时，需要刷新 |
| `x-zed-edit-predictions-usage-limit` | 编辑预测使用限制 |
| `x-zed-edit-predictions-usage-amount` | 编辑预测已使用量 |
| `x-zed-server-supports-status-messages` | 服务端支持状态消息 |
| `x-zed-minimum-required-version` | 最低要求版本 |

### 2.3 流式响应格式

当服务器支持状态消息时，每一行是一个 JSON：

```json
// 状态事件
{"Status": {"Queued": {"position": 0}}}
{"Status": "Started"}
{"Status": {"Failed": {"code": "...", "message": "...", "request_id": "uuid", "retry_after": null}}}
{"Status": "StreamEnded"}

// 上游 provider 原始事件
{"Event": { /* provider 原始 event */ }}
{"Event": { /* provider 原始 event */ }}
```

当服务器不支持状态消息时，每一行直接是 provider 原始事件的 JSON。

### 2.4 请求示例

以 Anthropic 为例，经过 `into_anthropic()` 转换后的 `provider_request`：

```json
{
  "model": "claude-sonnet-4-20250514",
  "max_tokens": 8192,
  "messages": [
    {
      "role": "user",
      "content": [
        {"type": "text", "text": "Hello"}
      ]
    }
  ],
  "tools": [],
  "stream": true
}
```

Zed 的 Cloud 代理层收到后，会：
1. 验证 LLM Token
2. 将 `provider_request` 转发到对应上游（如 `api.anthropic.com/v1/messages`）
3. 将上游的 SSE 响应以 JSON Lines 格式转发回客户端

---

## 三、LLM Token 认证机制

### 3.1 获取 Token

```
POST /client/llm_tokens
Authorization: {user_id} {access_token}
Content-Type: application/json

{
  "organization_id": "org-uuid"
}
```

认证方式使用 `user_id + access_token` 组合，格式为 `{user_id} {access_token}`。

### 3.2 Token 生命周期

```
┌─────────┐     ┌──────────────┐     ┌───────────────┐
│ 登录 Zed │────▶│ 获取 LLM     │────▶│ 使用 Bearer   │
│ (GitHub  │     │ Token (缓存) │     │ Token 请求    │
│  OAuth)  │     └──────────────┘     └───────┬───────┘
└─────────┘                                   │
                                              │ 401 或
                                              │ x-zed-expired-token
                                              ▼
                                      ┌─────────────────┐
                                      │ 刷新 Token       │
                                      │ 重试请求          │
                                      └─────────────────┘
```

### 3.3 认证流程

```
1. Client 启动 → 检查本地 credential
2. 无 credential  → 打开浏览器到 zed.dev 进行 GitHub OAuth
3. OAuth 回调 → 获取 access_token + user_id
4. 存储 credential → WebSocket 连接 wss://cloud.zed.dev/client/users/connect
5. 初始化 CloudLanguageModelProvider → 获取 LLM Token
6. 发送 AI 请求时附上 Bearer Token
```

WebSocket 连接用于实时通知（如 `UserUpdated`），使用 CBOR 序列化。

---

## 四、ACP (Agent Communication Protocol)

ACP 是 Zed 与外部 Agent 进程通信的协议，基于 JSON-RPC 2.0。

### 4.1 协议特点

- **传输层**: stdin/stdout (子进程)
- **协议**: JSON-RPC 2.0 (每行一个 JSON)
- **版本协商**: 初始化时交换 `ProtocolVersion`，当前最低支持 V1
- **双向通信**: Client (Zed) 和 Agent 都可发起请求、响应、通知

### 4.2 核心方法

#### 初始化
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": 1,
    "clientCapabilities": {
      "fs": { "readTextFile": true, "writeTextFile": true },
      "terminal": true,
      "auth": { "terminal": true }
    },
    "clientInfo": { "name": "zed", "version": "1.6.3" }
  }
}
```

#### Session 管理
| 方法 | 方向 | 说明 |
|------|------|------|
| `session/new` | Client→Agent | 创建新会话 |
| `session/load` | Client→Agent | 加载已有会话 |
| `session/resume` | Client→Agent | 恢复会话 |
| `session/close` | Client→Agent | 关闭会话 |
| `session/update` | Agent→Client | 会话更新通知 |

#### Prompt (AI 请求)
```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "prompt",
  "params": {
    "sessionId": "session-uuid",
    "messages": [...],
    "tools": [...]
  }
}
```

---

## 五、自带 Provider 实现

Zed 内置了多个 LLM Provider 的实现，可以直接连接上游 API：

| Provider | 请求端点 | 认证方式 |
|----------|----------|---------|
| **Anthropic** | `https://api.anthropic.com/v1/messages` | `X-Api-Key` |
| **OpenAI** | `https://api.openai.com/v1` | `Authorization: Bearer` |
| **Google** | `https://generativelanguage.googleapis.com/v1` | API Key |
| **xAI** | `https://api.x.ai/v1` | `Authorization: Bearer` |
| **Ollama** | 本地 HTTP | 无 |
| **LM Studio** | `http://localhost:1234/v1` | 无 |
| **DeepSeek** | `https://api.deepseek.com` | `Authorization: Bearer` |
| **OpenRouter** | `https://openrouter.ai` | `Authorization: Bearer` |
| **Mistral** | `https://api.mistral.ai/v1` | `Authorization: Bearer` |

---

## 六、关键发现 — 反向代理目标

要实现反向代理，核心需要劫持以下流量：

### 6.1 需要劫持的端点

| 端点 | 方法 | 用途 |
|------|------|------|
| `cloud.zed.dev/completions` | POST | LLM completion 请求 |
| `cloud.zed.dev/models` | GET | 获取可用模型列表 |
| `cloud.zed.dev/client/llm_tokens` | POST | 获取/刷新 LLM Token |
| `cloud.zed.dev/client/users/connect` | WebSocket | WebSocket 连接 |
| `cloud.zed.dev/client/users/me` | GET | 验证用户身份 |

### 6.2 需要模拟的认证行为

1. 获取 LLM Token 的 `POST /client/llm_tokens`（需要有效的 `user_id + access_token`）
2. Token 以 `Bearer {token}` 格式传递给 `/completions`
3. 如果返回 `x-zed-expired-token` 头则需要刷新 Token
4. 402 Payment Required 表示需要付费

### 6.3 服务端配置

Zed 通过 `ClientSettings.server_url` 配置服务端地址，默认 `https://zed.dev`，可通过 `ZED_SERVER_URL` 环境变量覆盖。

地址映射规则：
| server_url | cloud API base | LLM API base |
|-----------|---------------|--------------|
| `https://zed.dev` | `https://cloud.zed.dev` | `https://cloud.zed.dev` |
| `https://staging.zed.dev` | `https://cloud.zed.dev` | `https://llm-staging.zed.dev` |
| `http://localhost:3000` | `http://localhost:8787` | `http://localhost:8787` |

---

## 七、参考文件 (源码)

- `crates/language_model/src/language_model.rs` — LanguageModel trait
- `crates/language_model/src/registry.rs` — LanguageModelRegistry
- `crates/language_models_cloud/src/language_models_cloud.rs` — Cloud LLM 实现
- `crates/language_models/src/provider/cloud.rs` — CloudLanguageModelProvider
- `crates/cloud_llm_client/src/cloud_llm_client.rs` — 协议类型定义
- `crates/cloud_api_client/src/cloud_api_client.rs` — Cloud API 客户端
- `crates/client/src/client.rs` — 客户端核心 (认证、WebSocket)
- `crates/cloud_api_types/src/websocket_protocol.rs` — WebSocket 协议
- `crates/http_client/src/http_client.rs` — URL 构建逻辑
- `crates/agent_servers/src/acp.rs` — ACP 连接实现
