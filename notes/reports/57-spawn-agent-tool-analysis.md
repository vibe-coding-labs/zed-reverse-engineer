# 循环分析报告 #57 — Agent 子线程工具 (SpawnAgentTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/spawn_agent_tool.rs` (256 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`SpawnAgentTool` 允许 Agent 创建子线程（子 Agent），实现并行任务执行。

## 输入参数

```rust
pub struct SpawnAgentToolInput {
    pub label: String,                   // UI 显示标签
    pub message: String,                 // 子 Agent 的指令
    pub session_id: Option<acp::SessionId>, // 续已有会话（可选）
}
```

## 执行模式

- **新建会话**：`session_id=None` 时创建全新子 Agent 会话
- **续会话**：`session_id=Some(...)` 时续已有子 Agent 会话

## 并行模式

Agent 可以同时 spawn 多个子 Agent 并行执行任务，只要它们的写入范围不重叠。

## 输出

```rust
pub enum SpawnAgentToolOutput {
    Success {
        session_id: acp::SessionId,
        output: String,
        session_info: SubagentSessionInfo,
    },
    Error {
        session_id: Option<acp::SessionId>,
        error: String,
        session_info: Option<SubagentSessionInfo>,
    },
}
```

## 关键文件

- `crates/agent/src/tools/spawn_agent_tool.rs` — 子线程工具实现