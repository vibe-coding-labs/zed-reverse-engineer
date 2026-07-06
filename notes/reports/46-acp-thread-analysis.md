# 循环分析报告 #46 — ACP 线程管理层 (acp_thread)

**分析时间**: 2026-07-06
**源码位置**: `crates/acp_thread/src/` (10,091 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`acp_thread` 是 ACP 协议的线程/会话管理层，负责 Agent 会话的创建、消息传递、状态管理和工具调用处理。

## 核心类型

```rust
pub struct UserMessage {
    pub id: UserMessageId,
    pub content: String,
    pub attachments: Vec<Attachment>,
    pub sender: User,
}

pub struct AssistantMessage {
    pub id: MessageId,
    pub content: Vec<AssistantMessageChunk>,
    pub model: String,
}

pub enum AssistantMessageChunk {
    Text(String),
    Thinking(String),
    RedactedThinking(String),
    ToolCall(ToolCall),
    ReasoningDetails(String),
}
```

## 会话管理

```rust
pub struct AcpSession {
    pub session_id: acp::SessionId,
    pub messages: Vec<Message>,
    pub status: SessionStatus,
    pub created_at: DateTime<Utc>,
    pub updated_at: DateTime<Utc>,
}
```

## 连接管理

`connection.rs` 提供 `AgentConnection` trait 的扩展：

```rust
pub trait AgentConnection: Send + Sync {
    fn agent_id(&self) -> AgentId;
    fn new_session(...) -> Task<Result<Entity<AcpThread>>>;
    fn prompt(...) -> Task<Result<acp::PromptResponse>>;
    fn cancel(...);
    fn close_session(...) -> Task<Result<()>>;
    // ... 更多方法
}
```

## 关键功能

| 模块 | 行数 | 说明 |
|------|------|------|
| `acp_thread.rs` | 6,957 | 核心线程/会话管理 |
| `connection.rs` | 1,097 | Agent 连接抽象 |
| `mention.rs` | 1,277 | @提及解析 |
| `diff.rs` | 416 | Diff 差异展示 |

## 关键文件

- `crates/acp_thread/src/acp_thread.rs` — 核心实现
- `crates/acp_thread/src/connection.rs` — 连接抽象