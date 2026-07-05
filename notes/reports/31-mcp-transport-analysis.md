# 循环分析报告 #31 — MCP 完整传输层实现

**分析时间**: 2026-07-06
**源码位置**: `crates/context_server/src/` (5,155 行)
**分析前状态**: ⚠️ 看过 protocol 层但 transport 和 client 没碰过

## MCP 传输层

MCP 支持两种传输方式，由 `Transport` trait 统一抽象：

```rust
#[async_trait]
pub trait Transport: Send + Sync {
    async fn send(&self, message: String) -> Result<()>;
    fn receive(&self) -> Pin<Box<dyn Stream<Item = String> + Send>>;
    fn receive_err(&self) -> Pin<Box<dyn Stream<Item = String> + Send>>;
    fn set_protocol_version(&self, _version: &str) {}
}
```

### 1. stdio 传输 (`stdio_transport.rs`)

通过子进程 stdin/stdout 通信。每个 MCP 服务器启动一个子进程，Zed 通过 stdin 写入 JSON-RPC 请求，从 stdout 读取响应。

### 2. HTTP/SSE 传输 (`transport/http.rs`)

通过 HTTP + SSE (Server-Sent Events) 通信。从 `2025-06-18` 协议版本起，HTTP 传输需要在每个请求上附加 `MCP-Protocol-Version` 头。

## JSON-RPC 客户端

`client.rs` 实现了通用的 JSON-RPC 2.0 客户端：

- 标准 JSON-RPC 错误码：`-32700` (Parse)、`-32600` (Invalid Request)、`-32601` (Method Not Found)、`-32602` (Invalid Params)、`-32603` (Internal Error)
- 请求超时：默认 60 秒
- 支持请求取消（`Cancelled` 通知）
- 流式通知支持

## MCP OAuth 认证

`oauth.rs` (2,862 行 — 整个 crate 最大的文件) 实现了完整的 MCP OAuth 2.1 认证流程：
- PKCE (Proof Key for Code Exchange)
- 授权码流程
- SSRF 防护：OAuth 端点不允许指向私有 IP 地址

## 与反向代理的关系

MCP 是 LLM 工具调用协议，不参与 AI 请求的主要传输。不影响反向代理方案。

## 关键文件

- `crates/context_server/src/client.rs` — JSON-RPC 2.0 客户端 (594 行)
- `crates/context_server/src/protocol.rs` — MCP 协议生命周期 (132 行)
- `crates/context_server/src/transport.rs` — Transport trait 定义
- `crates/context_server/src/transport/http.rs` — HTTP/SSE 传输
- `crates/context_server/src/transport/stdio_transport.rs` — stdio 传输
- `crates/context_server/src/oauth.rs` — OAuth 2.1 + PKCE 认证 (2,862 行)