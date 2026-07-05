# 循环分析报告 #3 — MCP (Model Context Protocol) 集成

**分析时间**: 2026-07-04
**源码位置**: `crates/context_server/src/` (5,155 行)
**分析前状态**: ❌ 完全没碰过

## MCP 是什么

MCP (Model Context Protocol) 是 Anthropic 提出的开放协议，用于 LLM 与外部工具/数据源通信。Zed 实现了 **MCP 客户端** 侧，可以连接任意 MCP 服务器。

## 支持的传输方式

Zed 支持 **2 种 MCP 传输方式**：

### 1. stdio（标准输入输出）

```json
// settings.json 配置
"context_servers": {
  "my-server": {
    "command": "npx",
    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"],
    "env": { "KEY": "value" }
  }
}
```

Zed 启动子进程，通过 stdin/stdout 用 JSON-RPC 通信。

### 2. HTTP (SSE)

```json
"context_servers": {
  "my-server": {
    "url": "https://mcp.example.com/sse",
    "headers": { "Authorization": "Bearer xxx" }
  }
}
```

支持 OAuth 认证流程（`crates/context_server/src/oauth.rs`，2862 行），包括 PKCE + 授权码流程。

## MCP 协议版本

Zed 支持以下 MCP 协议版本：
- `2025-06-18` — 最新版
- `2025-03-26`
- `2024-11-05` — 原始版本

## 能力协商

初始化时交换能力：

```rust
// 客户端声明能力
ClientCapabilities {
    experimental: None,
    sampling: None,       // LLM sampling 请求
    roots: None,          // 文件系统根目录
}

// 服务器返回能力
ServerCapability::Experimental
ServerCapability::Logging
ServerCapability::Prompts
ServerCapability::Resources  // 文件资源
ServerCapability::Tools      // 工具调用
```

## 与 ACP 的关系

MCP 和 ACP 是两套不同的协议：
- **MCP**: LLM ↔ 工具/数据源（Zed 作为客户端）
- **ACP**: Zed ↔ 外部 Agent 进程（Zed 作为 Agent 的客户端）

两者都基于 JSON-RPC 2.0，但协议方法完全不同。

## 与反向代理的关系

Zed 的 MCP 集成不影响 AI 通信协议的劫持方案。MCP 是用于**扩展 LLM 能力**（工具调用、资源访问）的协议，不是 AI 请求本身的传输协议。

## 关键文件

- `crates/context_server/src/protocol.rs` — MCP 协议生命周期管理
- `crates/context_server/src/oauth.rs` — OAuth 2.1 + PKCE 认证（2862 行，非常完整）
- `crates/context_server/src/types.rs` — MCP 类型定义
- `crates/context_server/src/client.rs` — JSON-RPC 客户端
- `crates/context_server/src/transport.rs` — HTTP SSE 传输