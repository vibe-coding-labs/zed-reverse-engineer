# 分析报告 — 网络/HTTP crate 批量

| crate | 行数 | 用途 | AI 相关？ |
|-------|------|------|----------|
| `remote` | 6,921 | 远程开发 SSH 核心（已分析） | ⚠️ 远程功能 |
| `remote_server` | 5,851 | 远程 SSH 服务器（已覆盖） | ⚠️ |
| `http_client` | 1,309 | HTTP 客户端（已完整分析） | ✅ 已覆盖 |
| `remote_connection` | 728 | 远程连接管理 | ❌ |
| `net` | 442 | 网络工具函数 | ❌ |
| `reqwest_client` | 323 | Reqwest HTTP 实现 | ❌ |
| `aws_http_client` | 104 | AWS SigV4 签名客户端 | ⚠️ Bedrock 使用 |
| `http_client_tls` | 21 | TLS 配置 | ❌ |

核心 HTTP 客户端（`http_client`）已在深度分析中完整覆盖，包括 `HttpClientWithUrl` 的 URL 构建、代理读取、自定义头等。