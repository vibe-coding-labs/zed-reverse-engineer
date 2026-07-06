# 循环分析报告 #64 — 任务模板系统 (TaskTemplate)

**分析时间**: 2026-07-06
**源码位置**: `crates/task/src/task_template.rs` (1,154 行)
**分析前状态**: ❌ 完全没碰过

## 概述

TaskTemplate 是 Zed 的任务模板系统，定义命令如何从 JSON 配置转化为可执行任务。

## 核心结构

```rust
pub struct TaskTemplate {
    pub label: String,
    pub command: String,
    pub args: Vec<String>,
    pub env: HashMap<String, String>,
    pub cwd: Option<String>,
    pub use_new_terminal: bool,
    pub allow_concurrent_runs: bool,
    pub reveal: RevealStrategy,
    pub hide: HideStrategy,
    pub save: SaveStrategy,
    pub task_hook: Option<TaskHook>,
    pub tags: Vec<String>,
    pub debug_args: Option<DebugArgsRequest>,
}

pub enum RevealStrategy { Always, Never }
pub enum HideStrategy { Never, Always, OnSuccess }
pub enum SaveStrategy { All, Current, None }
pub enum DebugArgsRequest { Work, Ask }
pub enum TaskHook { CUSTOM_create_worktree }
```

## 变量替换

支持 `${variable}` 语法，在运行时替换为实际值：
- 项目路径、文件路径、光标位置
- 环境变量
- Git 信息

## 关键文件

- `crates/task/src/task_template.rs` — 任务模板定义与变量替换