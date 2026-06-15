# Zed 登录授权协议分析

## 概述

Zed 的认证体系分为三层：
1. **用户认证** — GitHub OAuth 登录，获取 `user_id` + `access_token`
2. **LLM Token** — 用于 AI 请求的短期 Bearer Token
3. **WebSocket 连接** — 保持与 cloud 服务的实时通信

---

## 一、用户认证流程

### 1.1 登录流程

```
┌──────────┐        ┌───────────┐         ┌──────────┐
│ Zed 客户端 │        │ cloud.zed │         │  GitHub   │
│           │        │  .dev     │         │          │
└─────┬─────┘        └─────┬─────┘         └────┬─────┘
      │                    │                     │
      │ 打开浏览器         │                     │
      │ ──────────────────▶│  OAuth 授权请求      │
      │                    │ ───────────────────▶│
      │                    │                     │
      │                    │  GitHub 登录页面     │
      │ 用户授权           │  ◀──────────────────│
      │                    │                     │
      │                    │  OAuth callback      │
      │                    │  (code)              │
      │                    │ ◀────────────────────│
      │                    │                     │
      │  返回 credential   │                     │
      │  (user_id + token) │                     │
      │ ◀──────────────────│                     │
      │                    │                     │
```

### 1.2 存储的凭证

凭证格式：`{user_id} {access_token}`

```
Credentials {
    user_id: u32,      // 用户 ID
    access_token: String,  // 访问令牌
}
```

凭证存储在本地，用于：
- HTTP 请求认证（`Authorization: {user_id} {access_token}`）
- WebSocket 连接认证

### 1.3 API 端点

| 端点 | 方法 | 用途 | 认证方式 |
|------|------|------|---------|
| `/client/users/me` | GET | 获取当前用户信息 | `{user_id} {access_token}` |
| `/client/llm_tokens` | POST | 创建 LLM Token | `{user_id} {access_token}` |
| `/client/users/connect` | WebSocket | 实时连接 | `{user_id} {access_token}` |
| `/client/system_settings` | PATCH | 更新系统设置 | `{user_id} {access_token}` |
| `/client/feedback/agent_thread` | POST | 提交 Agent 反馈 | `{user_id} {access_token}` |

所有端点都需要 `Content-Type: application/json` 头。

---

## 二、LLM Token 认证

### 2.1 Token 获取

```
POST /client/llm_tokens
Authorization: {user_id} {access_token}
Content-Type: application/json

{
  "organization_id": "org-uuid"
}
```

返回：
```json
{
  "token": "llm_xxxxx..."
}
```

### 2.2 Token 使用

```
POST /completions
Authorization: Bearer {llm_token}
Content-Type: application/json
x-zed-version: 1.6.3

{
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "provider_request": { ... }
}
```

### 2.3 Token 刷新机制

Token 由 `LlmApiToken` 结构体管理，支持：
- **缓存**: 按 `organization_id` 缓存，避免重复获取
- **自动刷新**: 服务端通过响应头 `x-zed-expired-token` 或 `x-zed-outdated-token` 通知过期
- **手动刷新**: `LlmApiToken::refresh()` 强制刷新
- **切换组织**: `LlmApiToken::clear_and_refresh()` 清除旧 Token 后重新获取

---

## 三、WebSocket 连接协议

### 3.1 建立连接

```
WebSocket: wss://cloud.zed.dev/client/users/connect

请求头:
  Authorization: {user_id} {access_token}
  x-zed-protocol-version: 0
```

### 3.2 心跳保活

- 每 1 秒发送一次 Ping 帧
- 连接断开时 Zed 会自动重连

### 3.3 消息格式

使用 CBOR (Concise Binary Object Representation) 序列化。

```rust
pub enum MessageToClient {
    UserUpdated,  // 用户信息已更新，需要刷新
}
```

Zed 收到 `UserUpdated` 后会刷新用户信息和组织配置。

### 3.4 重连时的模型刷新

Zed 监听 Cloud 连接 ID 的变化：
- 初始连接 `connection_id = 0` 时跳过
- 重连时 `connection_id > 0`，触发 debounced 模型列表刷新
- 刷新间隔：5 分钟 + 随机抖动

---

## 四、认证状态管理

### 4.1 状态机

```
SignedOut ──▶ SigningIn ──▶ Authenticated
                │               │
                │               ├── Reauthenticated (重连)
                │               │
                ▼               ▼
          Failed            SignedOut (退出)
```

### 4.2 状态变化处理

| 事件 | 行为 |
|------|------|
| 用户登录 | 获取 credential，建立 WebSocket 连接 |
| 连接断开 | 自动重连，状态变为 Reauthenticated |
| 用户登出 | 清除 credential，关闭连接，清除缓存模型列表 |
| Token 过期 | 刷新 LLM Token，重试请求 |
| 组织切换 | 清除并重新获取 LLM Token |

---

## 五、组织与计费

### 5.1 组织 ID

用户属于某个组织，LLM Token 与组织绑定的：

```rust
pub struct OrganizationId(Arc<str>);  // UUID 格式
```

### 5.2 计划类型

```rust
pub enum Plan {
    ZedFree,         // 免费 - 2,000 edit predictions
    ZedProTrial,     // Pro 试用 - 14天
    ZedPro,          // $10/月 - 无限 edit predictions + $5 额度
    ZedStudent,      // 学生计划
    ZedBusiness,     // $30/座位/月 - 企业管控
}
```

### 5.3 计费头

| 响应头 | 说明 |
|--------|------|
| `x-zed-edit-predictions-usage-limit` | 编辑预测使用上限 |
| `x-zed-edit-predictions-usage-amount` | 编辑预测已使用量 |

402 Payment Required 响应表示需要付费。

---

## 六、配置覆盖

### 6.1 环境变量

```bash
# 覆盖服务端地址
export ZED_SERVER_URL="http://localhost:3000"
```

### 6.2 客户端设置

```rust
pub struct ClientSettings {
    pub server_url: String,   // 默认: "https://zed.dev"
}
```

### 6.3 地址映射

| server_url | Cloud API | LLM API |
|-----------|-----------|---------|
| `https://zed.dev` | `https://cloud.zed.dev` | `https://cloud.zed.dev` |
| `https://staging.zed.dev` | `https://cloud.zed.dev` | `https://llm-staging.zed.dev` |
| `http://localhost:3000` | `http://localhost:8787` | `http://localhost:8787` |

---

## 七、安全要点

1. LLM Token 按 `OrganizationId` 缓存，切换组织自动清除
2. 所有 API 调用都需要认证，401 会被视为未授权
3. WebSocket 在建立连接时验证 Authorization 头
4. CBOR 序列化二进制消息比 JSON 更紧凑
5. 心跳保活间隔 1 秒，防止连接被关闭
