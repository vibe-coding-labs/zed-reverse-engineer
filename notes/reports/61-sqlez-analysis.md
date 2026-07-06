# 循环分析报告 #61 — SQLite 数据库层 (sqlez)

**分析时间**: 2026-07-06
**源码位置**: `crates/sqlez/src/` (2,612 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`sqlez` 是 Zed 的 SQLite 数据库封装层，提供线程安全的 SQLite 连接和查询接口。

## 核心模块

| 模块 | 行数 | 说明 |
|------|------|------|
| `connection.rs` | 532 | 数据库连接管理 |
| `statement.rs` | 497 | SQL 语句执行 |
| `bindable.rs` | 466 | 参数绑定（类型安全） |
| `migrations.rs` | 390 | 数据库迁移管理 |
| `typed_statements.rs` | — | 类型安全查询 |

## 使用场景

在 Zed 中，sqlez 用于：
- 会话持久化（Session）
- Agent 线程存储（ThreadsDatabase）
- 提示词存储（Prompt Store）
- 各种本地缓存

## 关键文件

- `crates/sqlez/src/connection.rs` — 数据库连接
- `crates/sqlez/src/migrations.rs` — 迁移管理
- `crates/sqlez/src/statement.rs` — 语句执行