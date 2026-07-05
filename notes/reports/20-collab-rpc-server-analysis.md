# 循环分析报告 #20 — Collab RPC 服务器 (多人协作)

**分析时间**: 2026-07-06
**源码位置**: `crates/collab/src/rpc.rs` (4,274 行) + `crates/collab/src/` 总计 15,205 行
**分析前状态**: ❌ 完全没碰过

## 概述

Collab 是 Zed 的多人协作服务器，处理所有实时协作通信。基于 WebSocket + protobuf 协议。

## 技术栈

- **HTTP 框架**: axum（`tower-http` + `async-tungstenite`）
- **WebSocket**: `tungstenite` WebSocket 升级
- **序列化**: protobuf（`rpc::proto::Envelope`）
- **数据库**: 自定义 `Database` trait（`crates/db/`）

## 认证

```rust
// crates/collab/src/auth.rs
// Authorization: {user_id} {access_token}
// 调用 cloud.zed.dev/client/users/me 验证
// 支持 dev-server-token（已废弃）
```

## 连接管理

```rust
// connection_pool.rs — 管理所有活跃的 WebSocket 连接
pub struct ConnectionPool;
// 跟踪每个连接的 ZedVersion 用于兼容性检查
```

## RPC 消息处理

Collab 服务器处理 250+ 种 protobuf 消息类型（定义在 `crates/proto/proto/`），包括：
- **项目**: ShareProject, JoinProject, UpdateBuffer
- **Git**: GitDiff, CreateBranch, Fetch, Rebase
- **频道**: ChannelMessage, JoinChannel, UpdateChannel
- **通话**: JoinRoom, IncomingCall, Call
- **LSP**: LspResponse, GetDefinition, GetCodeActions

## 与反向代理的关系

Collab 服务器是完整的服务端实现，与 AI 通信代理（`cloud.zed.dev`）是**独立的子系统**。反向代理不需要关心 Collab，只需拦截 `/completions` + `/models` + `/client/llm_tokens`。

## 关键文件

- `crates/collab/src/rpc.rs` — RPC 消息路由和处理（4,274 行）
- `crates/collab/src/auth.rs` — WebSocket 认证
- `crates/collab/src/db/queries/` — 数据库查询（rooms、projects、channels、buffers）