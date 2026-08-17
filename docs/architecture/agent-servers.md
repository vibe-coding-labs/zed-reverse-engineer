---
title: ACP 协议与外部 Agent 连接设计
description: AgentServer 统一抽象、ACP (JSON-RPC over stdio) 桥接、会话持久化
---

# ACP 协议与外部 Agent 连接设计

> **源码证据**: `/tmp/zed-src/zed-full/crates/agent_servers/`、`crates/acp_thread/`、`crates/agent/src/db.rs`

---

## 一、最核心的设计洞察

> **Zed 内置 Agent（NativeAgent）与外部 Agent（Claude Code / Codex / Gemini CLI）以完全相同的 ACP 会话语义对外提供服务。**

证据链：

```
NativeAgentServer 实现 AgentServer  trait（crates/agent/src/native_agent_server.rs）
    └─ connect() → 返回 Rc<dyn acp_thread::AgentConnection>
                                                        ▲
外部 ACP 服务器（claude/codex/gemini 子进程）           │ 统一的 trait
    └─ AcpConnection 实现 AgentConnection               │（acp_thread/src/connection.rs:91）

UI / Thread 通过 AgentConnection 抽象与两者交互 ────────┘
```

`AgentConnection` trait 定义的能力：

```rust
// crates/acp_thread/src/connection.rs:91
pub trait AgentConnection {
    fn agent_id(&self) -> AgentId;
    fn new_session(project, work_dirs, cx) -> Task<Result<Entity<AcpThread>>>;   // 新建会话
    fn supports_load_session() -> bool;       fn load_session(...)   -> ...;      // 加载历史
    fn supports_resume_session() -> bool;     fn resume_session(...) -> ...;      // 恢复不重放
    fn supports_session_history() -> bool;                                        // 支持会话历史
    fn auth_methods(&self) -> &[AuthMethod];                                       // 认证方式
    fn authenticate(&self, method, cx) -> Task<Result<()>>;
    fn prompt(params: PromptRequest, cx) -> Task<Result<PromptResponse>>;         // ★ 核心：向 agent 发提示
    fn retry(session_id, cx) -> Option<Rc<dyn AgentSessionRetry>>;
    fn cancel(session_id, cx);                                                     // 取消
    fn request_elicitations() -> Option<Entity<ElicitationStore>>;                 // 请求式干扰(elicitation)
}
```

---

## 二、支持的 Agent（AgentServer 注册表）

### 内置

| agent_id | 服务器 | 说明 |
|----------|--------|------|
| `Zed Agent` | `NativeAgentServer` | **内置 Agent**，走 `Thread` 引擎 + 工具系统 |
| `gemini` | `CustomAgentServer` | Google Gemini CLI（`crates/agent_servers/src/custom.rs` 里 `GEMINI_ID`） |
| `claude-acp` | `CustomAgentServer` | **Claude Code**（`CLAUDE_AGENT_ID`） |
| `codex-acp` | `CustomAgentServer` | OpenAI Codex CLI |
| `cursor` | `CustomAgentServer` | Cursor CLI |

### 外部扩展（ExternalAgentEntry）

`AgentServerStore`（`crates/project/src/agent_server_store.rs`）有 `external_agents: HashMap<AgentId, ExternalAgentEntry>`，从注册表发现（registry IDs）加载额外 agent：

```
"opencode" → opencode-cli
"mistral-vibe" → mistral-vibe CLI
"auggie" → auggie
...（EXTENSION_TO_REGISTRY_IDS 映射，可继续扩展）
```

### Store 三态

- **Local**: 本地项目，直接管理 node_runtime + Command
- **Remote**: 通过 `RemoteClient` 远端代理（命令序列化通过 proto `GetAgentServerCommand`）
- **Collab**: 协作会话模式

---

## 三、ACP 桥接的实现细节

`AcpConnection::stdio`（`crates/agent_servers/src/acp.rs:797`）是把外部 CLI 拉进 Zed 的核心。

### 进程启动（child process）

```rust
let builder = ShellBuilder::new(&Shell::System, cfg!(windows)).non_interactive();
let mut child = builder.build_std_command(Some(path), &args);
child.envs(env).current_dir(cwd);                       // 项目根目录
let mut child = Child::spawn(child, Stdio::piped(), Stdio::piped(), Stdio::piped())?;
// 三根管道：stdin / stdout / stderr
```

- 命令来自 `AgentServerCommand { path, args, env }`
- `stderr` 被 `AcpDebugLog` 记录（`AcpDebugMessageDirection::{Incoming, Outgoing, Stderr}`，默认保留最近 2000 条）
- **版本协商**：`MINIMUM_SUPPORTED_VERSION = ProtocolVersion::V1`，启动即发 `InitializeRequest::new(ProtocolVersion::V1)`，低于版本会报错

### JSON-RPC 2.0 over stdio

```
client → claude CLI:  { "jsonrpc":"2.0", "id":1, "method":"initialize", "params":{...} }
claude CLI → client: { "jsonrpc":"2.0", "id":1, "result":{...} }
```

- **in & out 都是 `lines()` 流**：`BufReader::new(stdout).lines()` 逐行解析，`lines()` sink 逐行写 stdin
- 每个 incoming request/notification 通过 `dispatch_tx`（unbounded mpsc）转发到 **foreground dispatch 队列**，由 `handle_*` 函数在 GPUI Context 上处理（解决 SDK handler 要求 `Send` 而 GPUI 是 `!Send` 的桥）
- 隐藏细节：unoptimized 构建下每个 inbound dispatch 需 ~0.5 MiB 栈，所以在独立线程上 poll

### 事件循环任务

| Task | 职责 |
|------|------|
| `_io_task` | 驱动连接（`connect_client_future`），transport 关闭即完成 |
| `_dispatch_task` | 消费 dispatch 队列，执行 `handle_prompt/handle_tool_call/...` |
| `_stderr_task` | 读取 stderr → debug log |
| `_wait_task` | 等待子进程退出；agent 异常退出时 Zed 清理会话 |

---

## 四、AcpThread：外部 Agent 的会话线程

`crates/acp_thread/src/acp_thread.rs`（10,197 行）在 Zed 侧维护每个外部 Agent 会话：

```
AcpThread（GPUI Entity）
  ├─ session_id: acp::SessionId
  ├─ messages: Vec<Message>            ← Zed 侧的消息镜像
  ├─ connection: Rc<dyn AgentConnection>  ← 通向 native 或 ACP
  ├─ user_message / diffs / terminals
  ├─ elicitations: ElicitationStore
  └─ PromptCapabilities（模型能力：image/embedded_context）
```

- **消息流**：用户在面板输入 → `PromptRequest` 发往 agent → agent 流式返回文本/工具调用 → Zed 以 `ThreadEvent` 广播到 UI
- **工具调用**：外部 Agent 的工具调用通过 `ToolCallUpdate`/`ToolCallUpdateFields` 更新状态、`ToolCallEventStream` 走同样的授权/沙箱管线
- **diff/terminal 共享**：外部 Agent 写入的文件同样生成 `Diff` 实体（绿/红高亮），终端输出同样受权限+截断控制 —— 与内置 Agent 体验完全一致

---

## 五、会话持久化（SQLite）

`crates/agent/src/db.rs`（1,249 行）—— 内置 Agent（NativeAgent）的 Thread 持久化，单表 key-value 设计：

```sql
CREATE TABLE IF NOT EXISTS threads (
    id          TEXT PRIMARY KEY,
    summary     TEXT NOT NULL,       -- 会话摘要（列表用）
    updated_at  TEXT NOT NULL,
    data_type   TEXT NOT NULL,       -- "thread"/"message" 等类型
    data        BLOB NOT NULL        -- 完整 Thread 序列化(zstd 压缩 level 3)
);
ALTER TABLE threads ADD COLUMN parent_id TEXT;      -- 子 Agent 指向父
ALTER TABLE threads ADD COLUMN folder_paths TEXT;   -- 会话目录
ALTER TABLE threads ADD COLUMN folder_paths_order TEXT;
ALTER TABLE threads ADD COLUMN created_at TEXT;
```

- `data_type` + `data BLOB`：一个 Thread 的所有消息、模型、配置整体序列化为 BLOB（`SerializedThread` = Thread + version）
- `ThreadStore::flush_to_db` 在**线程关闭/应用退出时**批量写入
- `Thread::from_db()` 恢复时反序列化 + 重新解析模型/主题/技能
- 子 Agent 线程通过 `parent_id` 挂到父线程；`folder_paths` 让会话可归入多个逻辑目录（agent UI 的分组依据）

---

## 六、密钥对话模型（NativeAgent 采用的同一套）

即使外部 Agent 是"黑盒"，Zed 侧依然用一套**与内置 Thread 完全相同的 UI/权限/沙箱管线**包装它。这把「外部 agent 接入」收敛成了一个非常纯粹的问题：**把 JSON-RPC 请求翻译成 AgentConnection 调用，把工具事件再翻译回来**。

```
┌──────────────────── Zed ────────────────────┐
│  UI(agent_ui)                                │
│    │ ThreadEvent(MessageAdded/ToolCall?)     │
│  AcpThread                                   │
│    │                                         │
│    └──↕ AgentConnection trait ───────────────┼──┐
│                                              │  │
│  NativeAgentServer         AcpConnection     │  │
│  (Thread引擎)               (子进程 stdio)     │  │
└──────────────────────────────────────────────┼──┘
                                               │
                    JSON-RPC 2.0 over stdio    │
                    claude CLI / codex / ...   ▼
```

---

## 七、与主仓库 AI 协议的关联

`agent-client-protocol` 是 **crates.io 的 ACP 2.0.0 SDK**（`Cargo.toml:523`：`agent-client-protocol = { version = "=2.0.0", features=["unstable"] }`）。Zed 用官方 SDK 做客户端，所以外部 Agent 接的是**标准 ACP 协议**——任何实现了 ACP 的 agent（Claude Code、Codex、Gemini、OpenCode 等）都能无修改接入。

> 关于 Zed Cloud 侧的 ACP 支持（远端 agent），另见 [AI 通信协议](../protocol/ai-protocol.md)。

---

## 参考

- `crates/agent_servers/src/agent_servers.rs` — AgentServer trait + Delegate
- `crates/agent_servers/src/acp.rs` — ACP 客户端桥
- `crates/agent_servers/src/custom.rs` — 内置自定义 agent 常量（gemini/claude-acp/codex-acp/cursor）
- `crates/acp_thread/src/acp_thread.rs` / `connection.rs` — 会话线程与连接抽象
- `crates/project/src/agent_server_store.rs` — 服务器注册表
- `crates/agent/src/db.rs` — SQLite 会话持久化