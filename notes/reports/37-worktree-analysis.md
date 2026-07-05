# 循环分析报告 #37 — Worktree (工作树/文件系统)

**分析时间**: 2026-07-06
**源码位置**: `crates/worktree/src/` (7,057 行) + `crates/project/src/worktree_store.rs` (1,398 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Worktree 是 Zed 的文件系统抽象层，管理项目文件、目录扫描、gitignore 过滤和文件变更检测。

## 核心功能

| 功能 | 说明 |
|------|------|
| 文件扫描 | 异步扫描目录树 |
| .gitignore 支持 | `ignore.rs` — 解析 .gitignore 规则 |
| 文件变更检测 | 监听文件系统事件 |
| 路径查询 | 按路径查找文件 |

## 与 AI Agent 的关系

Worktree 是 Agent 文件操作工具的基础：
- `ReadFileTool`、`WriteFileTool`、`EditFileTool` 依赖 Worktree 访问文件系统
- `ListDirectoryTool`、`FindPathTool`、`GrepTool` 依赖 Worktree 的扫描结果
- `CreateDirectoryTool`、`DeletePathTool` 等文件操作工具也依赖 Worktree

## 与反向代理的关系

不相关，本地文件系统操作。

## 关键文件

- `crates/worktree/src/worktree.rs` — 工作树核心 (6,819 行)
- `crates/worktree/src/ignore.rs` — .gitignore 解析
- `crates/project/src/worktree_store.rs` — 工作树存储