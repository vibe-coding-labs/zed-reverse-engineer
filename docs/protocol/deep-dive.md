---
title: 全链路深度分析
description: 从源码到二进制，Zed 通信协议、认证机制、架构设计的完整深度分析
---

# Zed 全链路深度分析

## 一、通信链路全景

### 1.1 URL 路由规则

Zed 使用 `HttpClientWithUrl` 管理所有出站请求，base_url 由 `ZED_SERVER_URL` 环境变量或 `ClientSettings.server_url` 控制：

| 目标 | server_url=zed.dev | server_url=localhost:3000 |
|------|-------------------|--------------------------|
| **Cloud API** | `https://cloud.zed.dev` | `http://localhost:8787` |
| **LLM API** | `https://cloud.zed.dev` | `http://localhost:8787` |
| **API** | `https://api.zed.dev` | `http://localhost:8080` |
| **Web** | `https://zed.dev` | `http://localhost:3000` |

**关键发现**：production 环境下 Cloud API 和 LLM API 指向**同一个域名**（`cloud.zed.dev`），staging 环境下 LLM 分离到 `llm-staging.zed.dev`。

### 1.2 请求头

所有出站请求使用标准 HTTP 请求，支持：
- `CustomHeaders` — 用户自定义头
- `RedirectPolicy` — 可配置重定向策略
- HTTP 代理：自动读取 `ALL_PROXY`/`HTTPS_PROXY`/`HTTP_PROXY`

---

## 二、认证全链路

### 2.1 认证状态机

```
SignedOut → Authenticating → Authenticated → Connected
                ↓                ↓
          Reauthenticating  Reauthenticated
                ↓                ↓
           SignedOut       ConnectionError/ConnectionLost
```

### 2.2 凭证存储

凭证存储在系统钥匙串中，URL 作为 key：
- **Linux**: libsecret (GNOME Keyring)
- **macOS**: system keychain
- **Dev mode**: `~/.config/zed/development_credentials`（文件存储）

### 2.3 sign_in 完整流程

```
1. 尝试内存中的旧凭证
   → 有效则直接返回
2. 尝试系统钥匙串中的凭证
   → 有效则直接返回，无效则删除
3. 都没有 → 走 OAuth 浏览器登录
   → authenticate_with_browser()
```

### 2.4 OAuth 完整流程

```
Zed 客户端:
1. 生成 RSA 2048-bit 密钥对
2. 公钥序列化: PKCS#1 DER → base64url
3. 启动本地 HTTP 服务器 (127.0.0.1:随机端口)
4. 打开浏览器到:
   /native_app_signin?port={port}&public_key={base64}

Zed 服务端:
5. 设置 state cookie → 302 到 GitHub OAuth
6. GitHub → 用户登录 + 授权
7. GitHub → cloud.zed.dev 回调
8. cloud.zed.dev 验证 state cookie
9. 用 RSA 公钥加密 access_token
10. 302 → localhost:{port}?user_id={id}&access_token={encrypted}

Zed 客户端:
11. 收到回调（最多等 100 秒）
12. 用私钥解密（OAEP-SHA256，回退 PKCS1v15）
13. 保存 Credentials {user_id, access_token}
```

### 2.5 管理员模拟登录

```bash
ZED_IMPERSONATE=github_username ZED_ADMIN_API_TOKEN=xxx zed

# 调用 cloud.zed.dev 内部 API
POST /internal/users/impersonate
Authorization: Bearer {admin_token}
{"github_login": "target_user"}
```

---

## 三、Edit Prediction（Zeta2）协议

Edit Prediction 是 Zed 自研的 Zeta2 模型，用于内联代码补全。

### 3.1 请求

```json
{
  "input_events": "base64_encoded_keystrokes",
  "input_excerpt": "current_buffer_content",
  "outline": "file_outline",
  "can_collect_data": true,
  "trigger": "buffer_edit"
}
```

### 3.2 反馈

```json
// 接受
POST /accept_edit_prediction
{"request_id": "uuid", "model_version": "...", "e2e_latency_ms": 1234}

// 拒绝（批量）
POST /reject_edit_predictions
{"rejections": [{"request_id": "uuid", "reason": "discarded", "was_shown": true}]}
```

拒绝原因：`Canceled`、`Empty`、`InterpolatedEmpty`、`Replaced`、`CurrentPreferred`、`Discarded`、`Rejected`

---

## 四、Collab RPC 协议

Zed 的多人协作基于 WebSocket + protobuf（协议版本 68）。

### 4.1 消息类型

从 `zed.proto` 的 `Envelope` 来看，支持 250+ 种消息类型：

| 类别 | 示例 |
|------|------|
| 房间/通话 | CreateRoom, JoinRoom, Call, IncomingCall |
| 项目协作 | ShareProject, JoinProject, AddCollaborator |
| LSP 代理 | GetDefinition, GetReferences, GetCompletions |
| Buffer 同步 | UpdateBuffer, SaveBuffer, BufferSaved |
| 文件操作 | CreateEntry, RenameEntry, DeleteEntry |
| Git 操作 | GetBranch, CreateBranch, GitDiff |
| 终端 | SpawnInTerminal, KillTerminal |

### 4.2 服务器认证

```rust
// 验证 Authorization 头: {user_id} {access_token}
// 调用 cloud.zed.dev/client/users/me 验证凭证
```

---

## 五、ACP 协议完整方法

基于 agent-client-protocol-schema v0.13.6：

| 方向 | 方法 | 说明 |
|------|------|------|
| 双向 | `initialize` | 版本 + 能力协商 |
| Client→Agent | `session/new` | 创建会话 |
| Client→Agent | `session/load` | 加载已有会话 |
| Client→Agent | `session/close` | 关闭会话 |
| Agent→Client | `session/update` | 会话更新 |
| Client→Agent | `auth/authenticate` | 认证 |
| Client→Agent | `auth/logout` | 登出 |
| Client→Agent | `prompt` | AI 请求 |

---

## 六、二进制交叉验证

从 Zed-editor 二进制（373 MB）中确认的符号：

```
环境变量: ZED_SERVER_URL, ZED_IMPERSONATE, ZED_ADMIN_API_TOKEN,
          ZED_DEVELOPMENT_USE_KEYCHAIN, ZED_WEB_LOGIN, ZED_RPC_URL

协议头: x-zed-edit-predictions-usage-limit,
        x-zed-edit-predictions-usage-amount,
        x-zed-protocol-version
```

---

## 参考

- `crates/http_client/src/http_client.rs` — HTTP 客户端实现
- `crates/client/src/client.rs` — 认证核心
- `crates/rpc/src/auth.rs` — RSA 加密
- `crates/zed_credentials_provider/src/lib.rs` — 凭证存储
- `crates/cloud_llm_client/src/cloud_llm_client.rs` — 协议类型定义
- `crates/edit_prediction_types/src/edit_prediction_types.rs` — Zeta2 协议
- `crates/proto/proto/zed.proto` — Collab RPC 协议定义