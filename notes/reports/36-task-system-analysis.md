# 循环分析报告 #36 — 任务系统 (Task)

**分析时间**: 2026-07-06
**源码位置**: `crates/task/src/` (3,003 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 的任务系统管理在终端中运行的命令任务，支持从 VS Code 任务格式转换。

## 核心类型

```rust
pub struct SpawnInTerminal {
    pub id: TaskId,
    pub label: String,
    pub command: Option<String>,
    pub args: Vec<String>,
    pub env: HashMap<String, String>,
    pub cwd: Option<String>,
    pub shell: Shell,
    pub use_new_terminal: bool,
    pub allow_concurrent_runs: bool,
    pub reveal: RevealStrategy,
    pub hide: HideStrategy,
    pub save: SaveStrategy,
    pub task_hook: Option<TaskHook>,
}
```

## 任务源

- **自定义任务**: 用户在 `tasks.json` 中定义
- **VS Code 兼容**: `vscode_format.rs` 和 `vscode_debug_format.rs` 导入 VS Code 任务配置
- **Agent 触发**: Agent 通过 `TerminalTool` 触发任务

## 执行流程

```
TaskTemplate → 变量替换 → ResolvedTask → SpawnInTerminal → 终端执行
```

## 与反向代理的关系

任务系统是本地执行，不涉及网络协议。

## 关键文件

- `crates/task/src/task_template.rs` — 任务模板定义和变量替换
- `crates/task/src/task.rs` — 核心任务类型
- `crates/task/src/vscode_format.rs` — VS Code 任务导入