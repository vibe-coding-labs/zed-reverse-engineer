# 循环分析报告 #51 — Agent 线程存储 (Thread Store)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/thread_store.rs` (314 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Thread Store 管理 Agent 会话线程的持久化存储——保存、加载、删除和列出线程。

## 核心功能

```rust
pub struct ThreadStore {
    threads: Vec<DbThreadMetadata>,
    reload_task: Shared<Task<()>>,
}
```

| 方法 | 说明 |
|------|------|
| `save_thread(id, thread, folder_paths)` | 持久化线程到数据库 |
| `load_thread(id)` | 从数据库加载线程 |
| `delete_thread(id)` | 删除单个线程 |
| `delete_threads()` | 删除所有线程 |
| `reload()` | 重新加载线程列表 |
| `entries()` | 返回所有线程元数据（按更新时间降序） |

## 数据库

使用 `ThreadsDatabase`（基于 `db` crate 的 SQLite/kvp 存储），线程 ID 使用 ACP 的 `SessionId`。

子线程（`parent_session_id.is_some()`）在 `entries()` 中被过滤，不会显示在主线程列表中。

## 关键文件

- `crates/agent/src/thread_store.rs` — 线程存储实现