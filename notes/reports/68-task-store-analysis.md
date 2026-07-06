# 循环分析报告 #68 — 任务存储 (TaskStore)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/task_store.rs` (504 行)
**分析前状态**: ❌ 完全没碰过

## 概述

TaskStore 管理项目的任务配置，负责从不同层次收集和解析任务定义。

## 结构

```rust
pub enum TaskStore {
    Local(StoreState),   // 本地项目
    Remote(StoreState),  // 远程项目
}
```

## 任务来源

任务定义从三个层次合并（低优先级 → 高优先级）：
1. **默认任务** — Zed 内置的默认任务模板（来自 `initial_tasks.json`）
2. **项目任务** — `.zed/tasks.json` 中的项目级配置
3. **用户任务** — `~/.config/zed/tasks.json` 中的用户级配置

## 与 Agent 的关系

Agent 通过 `SpawnInTerminal` 和 `TaskTemplate` 系统执行命令任务。TaskStore 提供任务配置的加载和解析。

## 关键文件

- `crates/project/src/task_store.rs` — 任务配置管理