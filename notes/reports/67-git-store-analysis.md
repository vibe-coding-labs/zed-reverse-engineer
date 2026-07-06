# 循环分析报告 #67 — Git 仓库状态管理 (GitStore)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/git_store.rs` (10,168 行)
**分析前状态**: ❌ 完全没碰过

## 概述

GitStore 管理 Git 仓库的状态跟踪，包括分支、提交、状态检查、diff 等。

## 核心结构

```rust
pub struct GitStore {
    repository: RepositoryEntry,
    branches: Vec<Branch>,
    status: HashMap<PathBuf, StatusEntry>,
    remotes: Vec<Remote>,
}

pub enum GitAccess { Local, Remote { project_id: u64 } }

pub struct StatusEntry {
    pub path: PathBuf,
    pub status: FileStatus,  // modified, added, deleted, etc.
    pub staged: bool,
}
```

## 与 AI Agent 的关系

Agent 通过 Git 相关工具：
- 读取文件变更状态（诊断上下文）
- 创建分支和提交
- 查看 diff（Agent 的工具调用的基础）
- 管理远程仓库

## 关键文件

- `crates/project/src/git_store.rs` — Git 状态管理（10,168 行）