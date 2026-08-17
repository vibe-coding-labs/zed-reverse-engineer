---
title: ACP 协议客户端方法清单与消息流
description: Zed 作为 ACP 客户端完整收发方法清单、握手、会话通知联合类型、终端事件流
---

# ACP 协议客户端方法清单与消息流

> **源码证据**: `/tmp/zed-src/zed-full/crates/agent_servers/src/acp.rs`（~5,000 行）、`crates/acp_thread/`

---

## 一、Zed 在 ACP 中的角色：**Client（宿主）**

外部 agent（Claude Code / Codex / Gemini）是实现 ACP 的 **Agent**，Zed 是 **Client**：

```
┌─────────────────────────── Zed (Client) ───────────────────────────┐
│                                                                     │
│  AcpConnection                                                      │
│    ├─ client_client_protocol::Client（SDK 客户器侧）                 │
│    ├─ connection: ConnectionTo<Agent>（发往 agent 的句柄）           │
│    └─ dispatch_tx → ForegroundWork（agent 消息→内部 handle_*）       │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ JSON-RPC 2.0 over stdio
                                │ (每行一条 JSON 消息, stdout/stdin)
    ┌───────────────────────────▼─────────────────────────────────────┐
    │                   外部 Agent 进程 (Agent 角色)                    │
    │   claude CLI / codex / gemini ...（通过 ShellBuilder spawn）      │
    └──────────────────────────────────────────────────────────────────┘
```

**协议版本**：`MINIMUM_SUPPORTED_VERSION = ProtocolVersion::V1`（`acp.rs:663`）。**SDK**：crates.io `agent-client-protocol = 2.0.0`（`Cargo.toml:523`）。

---

## 二、握手（initialize）

连接建立后 Zed 立即发 `InitializeRequest`：

```rust
// acp.rs:993
acp::InitializeRequest::new(ProtocolVersion::V1)
  // 还携带 client capabilities（agent 根据这些选择能力）
// 响应 < MINIMUM_SUPPORTED_VERSION → 拒绝连接
```

`client_capabilities_for_agent(&AgentId)` 按不同 agent（codex-acp 等）微调能力声明。

---

## 三、Zed 发给 agent 的请求（outgoing Request/Notification）

### Requests（期望响应）

| 方法 | 触发场景 | 关键字段 |
|------|---------|---------|
| `initialize` | 连接建立 | protocol_version |
| `new_session` | 用户新建会话 | session_id, work_dirs, project 元数据, mcp_servers |
| `set_session_mode` | 切换模式 | session_id, mode_id |
| `set_session_config_option` | 配置项 | session_id, config_id, value_id |
| `prompt` | **用户发消息**（核心） | session_id, message 内容块数组 |
| `list_sessions` | 会话列表刷新 | （可选） |
| `authenticate` | 触发 agent 认证 | auth_method_id |
| `logout` | 登出 | — |
| `close_session` | 关闭会话 | session_id |
| `delete_session` | 删除会话 | session_id |

### Notifications（fire-and-forget）

| 方法 | 触发 |
|------|------|
| `cancel` | `CancelNotification::new(session_id)` 用户点停止 |

---

## 四、agent 发给 Zed 的请求/通知（incoming）

### Requests（Zed 侧 handle_* 处理）

在 `connect_client_future` 中注册（`acp.rs:703-737`）：

| handler | 说明 |
|---------|------|
| `handle_request_permission` | ✨ agent 请求宿主授权（如执行某命令）→ 走 `PermissionOptions` 弹窗 |
| `handle_write_text_file` | agent 写文件 → 转成 `EditSession` 流式编辑 |
| `handle_read_text_file` | agent 读文件 |
| `handle_create_terminal` | agent 创建终端 |
| `handle_kill_terminal` | 杀死终端 |
| `handle_release_terminal` | 释放终端 |
| `handle_terminal_output` | 请求终端输出 |
| `handle_wait_for_terminal_exit` | 等待终端退出（给 agent 的命令阻塞语义） |
| `handle_create_elicitation` | 创建干扰(elicitation，如要求用户输入/确认) |

### Notifications（`handle_session_notification`）

核心是 **`SessionUpdate` 联合类型**（`acp::SessionUpdate`），承载 agent 会话的所有状态变化：

```rust
pub enum SessionUpdate {
    CurrentModeUpdate(...),      // 当前模式变化
    ConfigOptionUpdate(...),     // 配置选项变化
    MetaUpdate(...),
    SessionInfoUpdate(...),      // 会话信息（标题等）
    ToolCall(ToolCall),          // 工具调用开始（含初始字段）
    ToolCallUpdate(ToolCallUpdate), // 工具调用增量更新（状态/输出/终端meta）
    UserMessageUpdate(...),      // 用户消息更新
    AuthUpdate(...),
    CompactionUpdate(...),       // 压缩状态
}
```

**特殊 meta 消息**（ToolCall/ToolCallUpdate 的 `meta` 字段扩展协议）：
- `meta.terminal_info` — 附带终端创建（Zed 建"display-only"终端显示 agent 命令）
- `meta.terminal_output` — 流式终端输出
- `meta.terminal_exit` — 终端退出状态
- 以及在 Zed 侧定义/写入的：`tool_name`、`command_category`、`sandbox_authorization`、`sandbox_fallback_authorization`、`sandbox_not_applied`、`subagent_session_info`、`refusal_fallback` 等

### `handle_complete_elicitation`（Notification）

agent 完成一次 elicitation 时通知 Zed（回调用户回复/URL 完成等）。

---

## 五、双向关键消息流（一次完整对话）

```
用户输入 → AcpThread::prompt
  → Zed:  (Request)  prompt { session_id, message }
  → Agent: (Notif)   SessionUpdate::UserMessageUpdate { text chunk }
  → Agent: (Notif)   SessionUpdate::ToolCall { name, input... }        [工具即将执行]
  → Agent: (Request) handle_request_permission { ... }                 [需授权]
  → Zed 弹权限窗 → 返回 PermissionOption（允许/拒绝/总是）
  → Agent: (Notif)   SessionUpdate::ToolCallUpdate { output/status }
      └─ 若 meta.terminal_output → Zed 流式渲染在终端对
  → Agent: (Notif)   SessionUpdate::SessionInfoUpdate { title }
  → Agent: (Notif)   SessionUpdate::ToolCallUpdate { status: completed, output }
  → Agent: (Notif)   SessionUpdate::MetaUpdate / CompactionUpdate ...
  → 循环直至: Zed 接 Cancel / agent 发 session_info 或 Option 完成
```

---

## 六、终端作为一等公民

外部 agent 的终端命令对 Zed 来说是强交互对象：

1. **创建**：agent 调 `handle_create_terminal` 或工具带 `terminal_info` meta
2. **命令执行**：terminal 被 `display-only` 创建（无真实 PTY），Zed 把输出当数据流
3. **meta 流式输出**：命令的输出随 `SessionUpdate::ToolCallUpdate.meta.terminal_output` 每段推送
4. **退出**：`terminal_exit` 携带 exit_code/signal
5. **同步**：`wait_for_terminal_exit` 让 agent 阻塞等命令结束再继续

与内置 Agent 的 terminal_tool 在 UI 体验上**完全统一**。

---

## 七、权限请求协议

`handle_request_permission`（acp.rs:4582）是 agent 调用 Zed 权限系统的桥：

```
Agent: (Request) request_permission {
          id, title, options: [possible permission options], ... }
Zed:   → resolve 为 acp::PermissionOption（AllowAlways/RejectAlways/AllowOnce/RejectOnce...）
Zed:   → (Response) 结果
```

Zed 侧选项组装见 `authorize_third_party_tool`（Dropdown: allow+deny 配对 + sub_patterns）；授权持久化键如 `always_allow_mcp:{tool_id}`（MCP 工具）→ 存 settings `tool_permissions`。

---

## 八、会话生命周期方法

| 生命周期 | Zed 调用 | 说明 |
|---------|---------|------|
| 新建 | `new_session` → `AcpThread` | 先 `InitializeRequest` 再建 |
| 加载 | `supports_load_session` 判断 → `load_session` | 自动判断能力 |
| 恢复 | `supports_resume_session` → `resume_session` | 不重放历史 |
| 关闭 | `close_session` | Zed 侧释放 Session 结构 |
| 删除 | `delete_session` → `DeleteSessionRequest` | 库中清除 |
| 列表 | `list_sessions` → `AgentSessionListRequest` | UI 会话列表 |
| 取消 | `cancel` → `CancelNotification` | 轻量中止（不回滚） |

---

## 九、错误处理

ACP 错误码被 Zed 精细处理（`acp.rs:1965-2010`）：

| 错误 | Zed 行为 |
|------|---------|
| `ErrorCode::AuthRequired` | 转成 `AuthenticateError::AuthorizationRequired`，提示用户去认证 |
| `ErrorCode::InternalError` + data.details 含 abort 文案 | 转 `StopReason::Cancelled`（gemini 的已知 workaround，见 PR 引用） |
| 其他 `InternalError` | 按 details 字符串直接报错 |

> `suppress_abort_err` 标志：Zed 主动 cancel 后屏蔽接下来必然出现的 abort 错误，避免误报。

---

## 参考

- `crates/agent_servers/src/acp.rs` — `connect_client_future`（全部注册 handler）、`AcpConnection::prompt/cancel/delete`
- `crates/acp_thread/src/acp_thread.rs` — `prompt()` 组装、`run_turn` 语义
- 官方 SDK：crates.io `agent-client-protocol 2.0.0`（ACP 协议实现）
- 关联：[ACP 与外部 Agent 连接](agent-servers.md) · [Agent 工具系统](agent-tools.md)