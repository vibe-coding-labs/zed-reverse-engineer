# 分析报告 — Collab 数据库查询层

**源码位置**: `crates/collab/src/db/queries/`
**分析前状态**: ❌ 完全没碰过

## 概述

Collab 数据库查询层管理协作服务器的数据访问，使用多个查询模块。

## 查询模块

| 模块 | 说明 |
|------|------|
| `users.rs` | 用户查询和 GitHub 登录查找 |
| `rooms.rs` (1,445) | 房间/通话管理 |
| `projects.rs` (1,401) | 项目共享查询 |
| `channels.rs` (1,113) | 频道管理 |
| `buffers.rs` (1,049) | 缓冲区同步 |
| `contacts.rs` | 联系人管理 |
| `notifications.rs` | 通知管理 |
| `shared_threads.rs` | 共享 Agent 线程 |
| `extensions.rs` | 扩展同步 |
| `servers.rs` | 服务器管理 |
| `contributors.rs` | 贡献者管理 |

## 认证查询

```rust
pub async fn get_user_by_github_login(
    &self, github_login: &str
) -> Result<Option<User>> { ... }
```

用户认证通过 GitHub OAuth 完成后，用 `github_login` 查找本地用户记录。

## 关键文件

- `crates/collab/src/db/queries/users.rs` — 用户查询
- `crates/collab/src/entities/user.rs` — 用户实体定义