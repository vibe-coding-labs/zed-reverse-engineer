# 循环分析报告 #6 — LLM Token 刷新 & 代理机制

**分析时间**: 2026-07-05
**源码位置**: `crates/client/src/llm_token.rs` + `crates/client/src/proxy.rs`
**分析前状态**: ✅ 已知 Token 刷新，但细节不完整

## LLM Token 刷新完整机制

### 触发条件

LLM Token 在以下情况下刷新：

| 触发条件 | 方式 | 源码位置 |
|----------|------|----------|
| 响应头 `x-zed-expired-token` | 自动 | `NeedsLlmTokenRefresh` trait |
| 响应头 `x-zed-outdated-token` | 自动 | `NeedsLlmTokenRefresh` trait |
| 用户信息更新 (`UserUpdated` WebSocket) | 自动 | `handle_refresh_llm_token` |
| 切换组织 | 自动 (clear + refresh) | `OrganizationChanged` 事件 |
| 用户登出 | 自动清除 | `sign_out` 状态 |
| 手动调用 `refresh()` | 可选 | `LlmApiToken::refresh` |

### 刷新模式

```rust
enum TokenRefreshMode {
    Refresh,           // 直接刷新缓存
    ClearAndRefresh,   // 先清空再刷新（切换组织时）
}
```

### WebSocket 触发刷新

服务端通过 WebSocket 发送 `MessageToClient::UserUpdated` 消息，`RefreshLlmTokenListener` 收到后自动触发 Token 刷新。这是长连接的好处——不需要客户端轮询。

## 代理机制

Zed 客户端支持两种代理协议：

| 协议 | 实现 | 说明 |
|------|------|------|
| **HTTP CONNECT** | `proxy/http_proxy.rs` | 标准 HTTP 隧道代理 |
| **SOCKS5** | `proxy/socks_proxy.rs` | SOCKS5 代理 |

代理 URL 从 `ALL_PROXY` / `HTTPS_PROXY` / `HTTP_PROXY` 环境变量自动读取（参考 `read_proxy_from_env`）。

### 代理解析规则

```rust
// crate/http_client/src/http_client.rs:346-360
// 优先级: ALL_PROXY > all_proxy > HTTPS_PROXY > https_proxy > HTTP_PROXY > http_proxy
```

### 与反向代理的关系

这个代理机制说明了一个重要问题：**Zed 默认支持 HTTP 代理**。这意味着：
1. 不需要劫持 `ZED_SERVER_URL`，直接设置 `HTTPS_PROXY=http://localhost:3000` 也可以拦截流量
2. 但代理模式只能拦截 HTTP 流量，无法处理 WebSocket 的认证
3. 对于 `/completions` 的劫持，`ZED_SERVER_URL` 方式更简单可靠

## 关键文件

- `crates/client/src/llm_token.rs` — Token 刷新监听器（137 行）
- `crates/client/src/proxy.rs` — 代理连接（66 行，框架代码）
- `crates/client/src/proxy/http_proxy.rs` — HTTP CONNECT 实现
- `crates/client/src/proxy/socks_proxy.rs` — SOCKS5 实现