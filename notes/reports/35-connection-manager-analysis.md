# 循环分析报告 #35 — 项目连接管理器 (Connection Manager)

**分析时间**: 2026-07-06
**源码位置**: `crates/project/src/connection_manager.rs` (219 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Connection Manager 管理项目与远程协作服务器的连接状态，在断线时自动重连并恢复项目状态。

## 重连机制

```
客户端连接丢失 → 等待 30 秒超时
  ├── 客户端重连成功 → 发送 RejoinRemoteProjects
  │   ├── 服务端返回 rejoined_projects → 恢复项目
  │   └── 失败 → 最多重试 3 次
  └── 超时 → 关闭所有远程项目
```

## 关键参数

- 重连超时：30 秒
- 最大重试次数：3 次
- 重连后恢复：工作树扫描+仓库状态

## 与 AI 的关系

当远程项目断开连接时，AI Agent 也会失去访问权限。这不是协议层面的事，不影响反向代理方案。

## 关键文件

- `crates/project/src/connection_manager.rs` — 连接管理器