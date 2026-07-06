# 循环分析报告 #42 — Agent 核心引擎 (NativeAgent)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/agent.rs` (6,624 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`NativeAgent` 是 Zed 内置 AI Agent 的核心实现，管理 LLM 调用、工具执行、会话状态。

## 核心类型

```rust
pub struct NativeAgent {
    // 项目快照
    project: Entity<Project>,
    // 可用模型列表
    models: LanguageModels,
    // 技能加载状态
    skills_scan_task: Option<Task<()>>,
    // 语言模型提供者
    language_model_registry: Entity<LanguageModelRegistry>,
    // ACP 连接
    acp_connection: Option<Rc<dyn AgentConnection>>,
}

pub struct LanguageModels {
    provider: Arc<dyn LanguageModelProvider>,
    models: Vec<Arc<dyn LanguageModel>>,
    // 默认模型
    default: Option<ConfiguredModel>,
    // 快速模型
    default_fast: Option<ConfiguredModel>,
}

pub struct NativeAgentConnection(pub Entity<NativeAgent>);
```

## 关键功能

| 组件 | 说明 |
|------|------|
| `NativeAgent` | AI Agent 主引擎，管理 LLM 调用和会话 |
| `NativeAgentConnection` | 将 NativeAgent 包装为 ACP 兼容连接 |
| `NativeAgentSessionList` | 会话列表管理 |
| `NativeSubagentHandle` | 子 Agent 管理（并行 Agent） |
| `AcpTerminalHandle` | ACP 终端操作 |

## 状态管理

Agent 内部状态包括：
- 模型选择和切换
- 技能加载和扫描
- 会话生命周期
- 文件编辑状态

## 关键文件

- `crates/agent/src/agent.rs` — NativeAgent 核心实现 (6,624 行)