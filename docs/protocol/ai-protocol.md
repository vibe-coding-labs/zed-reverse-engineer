---
title: AI 通信协议分析
description: 深入分析 Zed 编辑器与 cloud.zed.dev 的 AI 通信协议
---

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
                    │
                    ▼
          ┌─────────────────────┐
          │   cloud.zed.dev     │
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

`provider_request` 字段直接透传上游 provider 格式的请求体。

### 2.2 关键 HTTP 头

| 请求头 | 说明 |
|--------|------|
| `Authorization: Bearer {token}` | LLM 认证 Token |
| `x-zed-version` | 客户端版本号 |
| `x-zed-client-supports-status-messages` | 客户端支持状态消息 |
| `x-zed-client-supports-x-ai` | 支持 xAI 模型 |

| 响应头 | 说明 |
|--------|------|
| `x-zed-expired-token` | Token 过期，需要刷新 |
| `x-zed-outdated-token` | Token 结构过时，需要刷新 |
| `x-zed-edit-predictions-usage-limit` | 编辑预测使用限制 |
| `x-zed-edit-predictions-usage-amount` | 编辑预测已使用量 |
| `x-zed-minimum-required-version` | 最低要求版本 |

### 2.3 流式响应格式

当服务器支持状态消息时，每一行是一个 JSON：

```json
// 状态事件
{"Status": {"Queued": {"position": 0}}}
{"Status": "Started"}
{"Status": {"Failed": {...}}}
{"Status": "StreamEnded"}

// 上游 provider 原始事件
{"Event": { /* provider 原始 event */ }}
```

当服务器不支持状态消息时，每一行直接是 provider 原始事件的 JSON。

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

---

## 四、ACP (Agent Communication Protocol)

ACP 是 Zed 与外部 Agent 进程通信的协议，基于 JSON-RPC 2.0。

### 4.1 协议特点

- **传输层**: stdin/stdout (子进程)
- **协议**: JSON-RPC 2.0 (每行一个 JSON)
- **版本协商**: 初始化时交换 `ProtocolVersion`，当前最低支持 V1
- **双向通信**: Client (Zed) 和 Agent 都可发起请求、响应、通知

### 4.2 核心方法

| 方法 | 方向 | 说明 |
|------|------|------|
| `initialize` | 双向 | 协议版本+能力协商 |
| `session/new` | Client→Agent | 创建新会话 |
| `session/load` | Client→Agent | 加载已有会话 |
| `session/close` | Client→Agent | 关闭会话 |
| `session/update` | Agent→Client | 会话更新通知 |
| `prompt` | Client→Agent | AI 请求 |

---

## 五、自带 Provider 实现

| Provider | 请求端点 | 认证方式 |
|----------|----------|---------|
| **Anthropic** | `api.anthropic.com/v1/messages` | `X-Api-Key` |
| **OpenAI** | `api.openai.com/v1` | `Authorization: Bearer` |
| **Google** | `generativelanguage.googleapis.com` | API Key |
| **xAI** | `api.x.ai/v1` | `Authorization: Bearer` |
| **Ollama** | 本地 HTTP | 无 |
| **LM Studio** | `localhost:1234/v1` | 无 |

---

## 六、服务端地址映射

| server_url | Cloud API | LLM API |
|-----------|-----------|---------|
| `https://zed.dev` | `https://cloud.zed.dev` | `https://cloud.zed.dev` |
| `http://localhost:3000` | `http://localhost:8787` | `http://localhost:8787` |

---

## 参考

- `crates/language_model/src/language_model.rs` — LanguageModel trait
- `crates/language_models_cloud/src/language_models_cloud.rs` — Cloud LLM 实现
- `crates/language_models/src/provider/cloud.rs` — CloudLanguageModelProvider
- `crates/agent_servers/src/acp.rs` — ACP 连接实现