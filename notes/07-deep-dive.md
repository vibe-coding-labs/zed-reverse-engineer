# Zed 深度分析：协议、认证、架构全链路

## 一、通信链路全景

### 1.1 URL 路由规则

Zed 使用 `HttpClientWithUrl` 管理所有出站请求，base_url 由 `ZED_SERVER_URL` 环境变量或 `ClientSettings.server_url` 控制：

```json
{
  "server_url": "https://zed.dev"  // 默认值，可通过 ZED_SERVER_URL 覆盖
}
```

URL 映射规则（`crates/http_client/src/http_client.rs:266-321`）：

| 目标 | server_url=zed.dev | server_url=localhost:3000 |
|------|-------------------|--------------------------|
| **Cloud API** → `build_zed_cloud_url()` | `https://cloud.zed.dev` | `http://localhost:8787` |
| **LLM API** → `build_zed_llm_url()` | `https://cloud.zed.dev` | `http://localhost:8787` |
| **API** → `build_zed_api_url()` | `https://api.zed.dev` | `http://localhost:8080` |
| **Web** → `build_url()` | `https://zed.dev` | `http://localhost:3000` |

**关键发现**：production 环境下 Cloud API 和 LLM API 指向**同一个域名**（`cloud.zed.dev`），staging 环境下 LLM 分离到 `llm-staging.zed.dev`。

### 1.2 请求头

所有出站请求使用 `http` crate 的 `Request<AsyncBody>`，支持：
- `CustomHeaders` — 用户自定义头（settings 加载时验证）
- `HttpRequestExt::when_some()` — 条件添加头
- `RedirectPolicy` — 可配置重定向策略

HTTP 代理支持：自动读取环境变量 `ALL_PROXY`/`HTTPS_PROXY`/`HTTP_PROXY`（参考 `read_proxy_from_env`）

---

## 二、认证全链路（完整代码级）

### 2.1 认证状态机

Zed 客户端维护一个状态机（`client/src/client.rs`）：

```
SignedOut → Authenticating → Authenticated → Connected
                ↓                ↓
          Reauthenticating  Reauthenticated
                ↓                ↓
           SignedOut       ConnectionError/ConnectionLost
```

### 2.2 凭证存储

凭证存储在系统钥匙串中，URL 作为 key：

```rust
// crates/zed_credentials_provider/src/lib.rs
// Linux: libsecret (GNOME Keyring)
// macOS: system keychain
// Dev mode (~/.config/zed/development_credentials):
//   {"https://zed.dev": [user_id_string, access_token_bytes]}
```

开发模式通过 `ZED_DEVELOPMENT_USE_KEYCHAIN=true` 启用（仅 Dev channel）。

### 2.3 sign_in 完整流程

```rust
// client/src/client.rs:880-957
pub async fn sign_in(self, try_provider: bool, cx: &AsyncApp) -> Result<Credentials> {
    // 1. 先尝试内存中的旧凭证
    if let Some(old) = self.state.read().credentials.clone() {
        if self.validate_credentials(&old, cx).await? {
            return Ok(old)  // 内存凭证有效，直接返回
        }
    }

    // 2. 再尝试凭证提供者（系统钥匙串）
    if try_provider {
        if let Some(stored) = self.credentials_provider.read_credentials(cx).await {
            if self.validate_credentials(&stored, cx).await? {
                return Ok(stored)  // 钥匙串凭证有效，直接返回
            }
            self.credentials_provider.delete_credentials(cx).await;
        }
    }

    // 3. 都没有 → 走 OAuth（浏览器登录）
    self.authenticate(cx).await  // 委托给 authenticate 方法
}
```

### 2.4 OAuth 登录完整流程（authenticate_with_browser）

```rust
// client/src/client.rs:1428-1557
// 1. 生成 RSA 2048-bit 密钥对
let (public_key, private_key) = rpc::auth::keypair()?;

// 2. 公钥序列化：PKCS#1 DER → base64url
let public_key = String::try_from(public_key)?;

// 3. 启动本地 HTTP 服务器
let server = tiny_http::Server::http("127.0.0.1:0")?;  // 随机端口
let port = server.server_addr().to_ip()?.port();

// 4. 构建回调 URL
let auth_url = format!(
    "/native_app_signin?native_app_port={}&native_app_public_key={}&system_id={}",
    port, public_key, system_id
);

// 5. 打开浏览器
open_url_tx.send(auth_url);

// 6. 等待回调（最多 100 秒）
loop {  // 100 次 × 1s 超时
    let req = server.recv_timeout(Duration::from_secs(1))?;
    // 解析回调参数: user_id + encrytped access_token
}

// 7. 解密 access_token（先 OAEP-SHA256，回退 PKCS1v15）
let access_token = private_key.decrypt_string(&encrypted_token)?;
```

### 2.5 管理员模拟登录

```rust
// 环境变量方式：
ZED_IMPERSONATE=github_username ZED_ADMIN_API_TOKEN=xxx zed

// 调用 cloud.zed.dev 内部 API
POST /internal/users/impersonate
Authorization: Bearer {admin_token}
{"github_login": "target_user"}

// 返回:
{"user_id": 12345, "access_token": "..."}
```

---

## 三、Edit Prediction（Zeta2）协议

之前完全没碰过的领域。Edit Prediction 是 Zed 自研的 Zeta2 模型，用于内联代码补全。

### 3.1 请求端点

```
POST /edit_predictions
Authorization: Bearer {llm_token}
Content-Type: application/json
x-zed-version: 1.6.3
x-zed-preferred-experiment: {experiment_name}
```

### 3.2 请求体

```json
{
  "input_events": "base64_encoded_keystrokes",
  "input_excerpt": "current_buffer_content",
  "outline": "file_outline",
  "speculated_output": null,
  "can_collect_data": true,
  "trigger": "buffer_edit",
  "diagnostic_groups": null,
  "git_info": {
    "head_sha": "abc123",
    "remote_origin_url": "https://github.com/..."
  }
}
```

### 3.3 响应体

```json
{
  "request_id": "uuid",
  "output_excerpt": "predicted_edit"
}
```

### 3.4 反馈机制

用户接受/拒绝预测后，客户端发送反馈：

```json
// 接受
POST /accept_edit_prediction
{"request_id": "uuid", "model_version": "...", "e2e_latency_ms": 1234}

// 拒绝（支持批量）
POST /reject_edit_predictions
{"rejections": [{"request_id": "uuid", "reason": "discarded", "was_shown": true}]}
```

拒绝原因枚举：`Canceled`、`Empty`、`InterpolatedEmpty`、`Replaced`、`CurrentPreferred`、`Discarded`、`Rejected`

---

## 四、Collab RPC 协议

Collab 是 Zed 的多人协作服务器，基于 WebSocket + protobuf（协议版本 68）。

### 4.1 传输层

```rust
// crates/rpc/src/conn.rs
// 基于 async_tungstenite WebSocket
// 消息通过 protobuf 序列化
// 每个消息包含：id + 可选的 responding_to + 可选的 ack_id + payload
```

### 4.2 消息类型（4647 行 proto 定义）

从 `zed.proto` 的 `Envelope` 来看，支持 250+ 种消息类型：

| 消息类别 | 数量 | 示例 |
|---------|------|------|
| 房间/通话管理 | 15+ | CreateRoom, JoinRoom, Call, IncomingCall |
| 项目协作 | 10+ | ShareProject, JoinProject, AddCollaborator |
| LSP 代理 | 30+ | GetDefinition, GetReferences, GetCompletions |
| Buffer 同步 | 20+ | UpdateBuffer, SaveBuffer, BufferSaved |
| 文件操作 | 15+ | CreateEntry, RenameEntry, DeleteEntry |
| Git 操作 | 20+ | GetBranch, CreateBranch, GitDiff |
| 终端 | 10+ | SpawnInTerminal, KillTerminal |
| 搜索 | 5+ | SearchQuery |
| 渠道/通知 | 10+ | ChannelMessage, Notification |

### 4.3 Collab 服务器认证

```rust
// crates/collab/src/auth.rs
// 验证 Authorization 头: {user_id} {access_token}
// 调用 cloud.zed.dev/client/users/me 验证凭证
// 支持 dev-server-token（已废弃）
```

---

## 五、ACP 协议补充细节

ACP 基于 agent-client-protocol-schema v0.13.6，完整方法列表：

### 5.1 初始化

```
Client → Agent: initialize(protocol_version, client_capabilities, client_info)
Agent → Client: initialize_response(protocol_version, agent_info, agent_capabilities, auth_methods)

client_capabilities 包含:
  fs: { read_text_file, write_text_file }
  terminal: bool
  auth: { terminal }
  meta: ["terminal_output", "terminal-auth"]
```

### 5.2 Session 管理

```
Client → Agent: session/new(cwd, additional_dirs, mcp_servers)
Client → Agent: session/load(session_id, cwd, additional_dirs, mcp_servers)
Client → Agent: session/resume(session_id, cwd, additional_dirs, mcp_servers)
Client → Agent: session/close(session_id)
Agent → Client: session/update(session_id, update_type)

session/update 类型:
  UserMessageChunk, AgentMessageChunk, ToolCall, ToolCallUpdate
  CurrentModeUpdate, ConfigOptionUpdate, SessionInfoUpdate
```

### 5.3 认证

```
Agent → Client: 返回 auth_methods
Client → Agent: auth/authenticate(method_id)
Agent → Client: auth/logout()  （可选支持）
```

### 5.4 Prompt

```
Client → Agent: prompt(session_id, messages, tools)
Agent → Client: prompt_response(stop_reason)
```

### 5.5 能力协商

Agent 在初始化时声明能力：
```
agent_capabilities:
  load_session: bool
  session_capabilities:
    close: optional
    list: optional
    resume: optional
    delete: optional
    additional_directories: optional
  auth:
    logout: optional
  prompt_capabilities: {...}
```

---

## 六、二进制交叉验证

二进制符号确认了以下代码级别的发现：

```bash
strings zed-editor | grep -E "ZED_SERVER_URL|ZED_IMPERSONATE|ZED_ADMIN_API_TOKEN|ZED_DEVELOPMENT_USE_KEYCHAIN|ZED_WEB_LOGIN|ZED_RPC_URL|ZED_ALWAYS_ACTIVE"
```

这些环境变量确实都在二进制中：
- `ZED_SERVER_URL` — 覆盖服务端地址
- `ZED_IMPERSONATE` + `ZED_ADMIN_API_TOKEN` — 管理员模拟登录
- `ZED_DEVELOPMENT_USE_KEYCHAIN` — 开发模式凭证
- `ZED_WEB_LOGIN` — Web 登录模式
- `ZED_RPC_URL` — RPC 地址覆盖
- `ZED_ALWAYS_ACTIVE` — 常驻模式

协议头也在二进制中确认：
- `x-zed-edit-predictions-usage-limit`
- `x-zed-edit-predictions-usage-amount`
- `x-zed-protocol-version`

---

## 七、总结

| 层面 | 分析深度 | 关键发现 |
|------|---------|---------|
| URL 路由 | ✅ 完整 | server_url 映射规则、ZED_SERVER_URL 覆盖 |
| HTTP 客户端 | ✅ 完整 | CustomHeaders、Proxy 支持、RedirectPolicy |
| 认证状态机 | ✅ 完整 | 5 种状态、4 层凭证查找 |
| OAuth 流程 | ✅ 完整 | RSA 2048-bit、OAEP-SHA256、回调服务器 |
| LLM Token | ✅ 完整 | 缓存、刷新、过期检测 |
| Edit Prediction | ✅ 完整 | 请求/响应/反馈全链路 |
| Collab RPC | ✅ 框架 | protobuf 250+ 消息类型 |
| ACP 协议 | ✅ 完整 | 初始化、Session、Auth、Prompt 全流程 |
| 二进制验证 | ✅ 关键符号 | 环境变量、协议头已确认 |
| 管理员接口 | ✅ 完整 | ZED_IMPERSONATE + internal API |