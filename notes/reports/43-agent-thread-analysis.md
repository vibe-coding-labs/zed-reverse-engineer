# 循环分析报告 #43 — Agent 线程核心 (Thread)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/thread.rs` (7,290 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`Thread` 是 AI Agent 会话线程的核心，管理 Agent 与 LLM 之间的对话历史、工具调用和响应流。

## 核心消息类型

```rust
pub enum Message {
    User(UserMessage),
    Agent(AgentMessage),
    System(SystemMessage),
}

pub struct UserMessage {
    pub id: UserMessageId,
    pub content: UserMessageContent,
    pub sender: Sender,        // 人类用户
    pub timestamp: DateTime<Utc>,
}

pub struct AgentMessage {
    pub id: MessageId,
    pub content: AgentMessageContent,  // 文本、thinking、工具调用
    pub source: ModelSource,   // 哪个模型生成的
    pub timestamp: DateTime<Utc>,
}
```

## 线程状态管理

```rust
pub enum ThreadEvent {
    MessageAdded,           // 新消息
    MessageRemoved,         // 消息删除
    MessageEdited,          // 消息编辑
    StatusChanged,          // 状态变更（生成中/已停止/出错）
    ToolCallStarted,        // 工具调用开始
    ToolCallFinished,       // 工具调用完成
    ContextCompaction,      // 上下文压缩（超长对话时）
}
```

## 关键功能

| 功能 | 说明 |
|------|------|
| 消息管理 | 添加、删除、编辑对话消息 |
| 模型调用 | 选择 LLM 模型并发送 prompt |
| 工具执行 | Agent 工具的声明、调用、结果处理 |
| 上下文压缩 | 超长对话时自动压缩历史（`CompactionInfo`） |
| 子线程支持 | `SubagentContext` 管理并行 Agent 线程 |
| Prompt 管理 | `PromptId` 标识可复用的 prompt 模板 |

## 子线程 (Sibling Thread)

```rust
pub struct SiblingThreadRequest {
    pub project_snapshot: ProjectSnapshot,
    pub model: AvailableModel,
    pub instruction: String,    // 给子 Agent 的指令
}

pub struct SiblingThreadInfo {
    pub thread_id: ThreadId,
    pub status: ThreadStatus,
}
```

支持**并行 Agent 子线程**——主 Agent 可以 spawn 子 Agent 独立执行任务。

## 事件处理

Agent 会话发生的事件通过 `ThreadEvent` 广播给 UI 层更新显示。UI 层根据这些事件渲染对话界面。

## 关键文件

- `crates/agent/src/thread.rs` — Thread 核心实现 (7,290 行)
- `crates/agent/src/agent.rs` — NativeAgent 管理 Thread 生命周期