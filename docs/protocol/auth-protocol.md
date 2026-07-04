---
title: 登录授权协议分析
description: 完整剖析 Zed 的 GitHub OAuth 登录流程和 LLM Token 认证机制
---

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
```

### 1.2 存储的凭证

凭证格式：`{user_id} {access_token}`

```rust
Credentials {
    user_id: u32,            // 用户 ID
    access_token: String,    // 访问令牌
}
```

凭证存储在系统 keychain 中。Linux 上存储在 libsecret，macOS 上存储在系统钥匙串。

### 1.3 API 端点

| 端点 | 方法 | 用途 | 认证方式 |
|------|------|------|---------|
| `/client/users/me` | GET | 获取当前用户信息 | `{user_id} {access_token}` |
| `/client/llm_tokens` | POST | 创建 LLM Token | `{user_id} {access_token}` |
| `/client/users/connect` | WebSocket | 实时连接 | `{user_id} {access_token}` |

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

{
  "provider": "anthropic",
  "model": "claude-sonnet-4-20250514",
  "provider_request": { ... }
}
```

### 2.3 Token 刷新机制

Token 由 `LlmApiToken` 结构体管理，支持：
- **缓存**: 按 `organization_id` 缓存，避免重复获取
- **自动刷新**: 服务端通过响应头 `x-zed-expired-token` 通知过期
- **手动刷新**: `refresh()` 强制刷新
- **切换组织**: `clear_and_refresh()` 清除旧 Token 后重新获取

---

## 三、OAuth 回调机制

### 3.1 流程细节

```
Zed 客户端:
1. 生成 RSA 2048-bit 密钥对
2. 启动本地 HTTP 服务器 (127.0.0.1:随机端口)
3. 打开浏览器到 zed.dev/native_app_signin?port=xxx&public_key=xxx

Zed 服务端 (cloud.zed.dev):
4. 设置 state cookie → 302 到 GitHub OAuth
5. GitHub → 用户登录 + 授权
6. GitHub → cloud.zed.dev/frontend/auth/github/callback
7. cloud.zed.dev 验证 state cookie
8. 用 code 向 GitHub API 交换 access_token
9. 用 RSA 公钥加密 access_token
10. 302 重定向到 localhost:{port}?user_id=xxx&access_token=加密值

Zed 客户端:
11. 收到回调 → 用私钥解密 access_token
12. 保存 Credentials {user_id, access_token}
```

### 3.2 RSA 加密细节

```python
# 密钥生成: RSA 2048-bit
# 公钥序列化: PKCS#1 DER → base64url
# 加密算法:
#   V1: OAEP with SHA-256 (首选)
#   V0: PKCS1v15 (回退)
# access_token 格式: 48 字节随机数 → base64url (64 字符)
```

---

## 四、WebSocket 连接协议

### 4.1 建立连接

```
wss://cloud.zed.dev/client/users/connect

请求头:
  Authorization: {user_id} {access_token}
  x-zed-protocol-version: 0
```

### 4.2 心跳保活

- 每 1 秒发送一次 Ping 帧
- 连接断开时 Zed 会自动重连

### 4.3 消息格式

使用 CBOR (Concise Binary Object Representation) 序列化。

```rust
pub enum MessageToClient {
    UserUpdated,  // 用户信息已更新，需要刷新
}
```

---

## 五、组织与计费

### 5.1 计划类型

```rust
pub enum Plan {
    ZedFree,         // 免费 - 2,000 edit predictions
    ZedProTrial,     // Pro 试用 - 14天 + $5额度
    ZedPro,          // $10/月 - 无限 edit predictions
    ZedStudent,      // 学生计划
    ZedBusiness,     // $30/座位/月 - 企业管控
}
```

### 5.2 计费响应

402 Payment Required 响应表示需要付费。响应头中还包含：
- `x-zed-edit-predictions-usage-limit` — 使用上限
- `x-zed-edit-predictions-usage-amount` — 已使用量

---

## 六、配置覆盖

```bash
# 环境变量覆盖服务端地址
export ZED_SERVER_URL="http://localhost:3000"

# 开发模式 - 使用文件存储凭证而非系统钥匙串
export ZED_DEVELOPMENT_USE_KEYCHAIN="true"

# 管理员模拟登录（需要 admin token）
export ZED_IMPERSONATE="github_username"
export ZED_ADMIN_API_TOKEN="admin_token"
```

---

## 参考

- `crates/client/src/client.rs` — 客户端核心 (认证、WebSocket)
- `crates/rpc/src/auth.rs` — RSA 加密认证实现
- `crates/cloud_api_client/src/cloud_api_client.rs` — Cloud API 客户端
- `crates/cloud_api_types/src/plan.rs` — 计划类型定义