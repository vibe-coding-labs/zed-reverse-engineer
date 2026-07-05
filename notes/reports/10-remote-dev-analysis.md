# 循环分析报告 #10 — 远程开发/SSH 协议

**分析时间**: 2026-07-05
**源码位置**: `crates/remote/src/` (2,799 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 支持远程开发：UI 在本地运行，代码在远程服务器上。通过 SSH 连接，使用 protobuf over TCP 传输。

## 传输协议

远程传输使用 **protobuf + 长度前缀** 的二进制协议：

```
[4字节小端长度][protobuf 编码的 Envelope]
```

协议定义在 `crates/remote/src/protocol.rs`，核心函数：
- `read_message()` — 从流中读取完整消息
- `write_message()` — 写入消息（自动添加长度前缀）

## 连接状态机

```rust
enum ConnectionState {
    // SSH 连接阶段
    Connecting,          // 正在建立 SSH 连接
    Authenticating,      // SSH 认证中
    Connected,           // 连接建立
    // 断开阶段
    ConnectionLost,      // 连接丢失
    Reconnecting,        // 正在重连
    Disconnected,        // 已断开
}
```

## 平台支持

```rust
enum RemoteOs { Linux, MacOs, Windows }
enum RemoteArch { Aarch64, X8664 }
```

远程服务器自动检测操作系统和架构。

## 与反向代理的关系

远程开发使用 SSH 隧道，不走 HTTP 代理。不影响 AI 通信协议的反向代理方案。

## 关键文件

- `crates/remote/src/remote_client.rs` — 远程客户端实现（1,977 行）
- `crates/remote/src/transport.rs` — 传输层
- `crates/remote/src/protocol.rs` — protobuf 帧协议