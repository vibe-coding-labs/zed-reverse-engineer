# 补覆盖分析 — 关键网络/认证 crate (cloud_api_types, cloud_api_client, credentials_provider 等)

## cloud_api_types (633 行)
**状态**: ✅ 已在分析中完整覆盖
Cloud API 类型定义，已在 `02-auth-protocol-analysis.md` 和 `protocol/auth-protocol` 中详细分析。包含 `GetAuthenticatedUserResponse`、`CreateLlmTokenBody`、`CreateLlmTokenResponse`、`PlanInfo`、`Plan`、`OrganizationId`、`LlmToken` 等核心类型。WebSocket 协议 `MessageToClient` 也在 `cloud_api_types/src/websocket_protocol.rs` 中覆盖。

## cloud_api_client (525 行)
**状态**: ✅ 已在分析中完整覆盖
Cloud API 客户端实现，已在协议分析中完整覆盖。包括 `GET /client/users/me`、`POST /client/llm_tokens`、WebSocket 连接 `wss://cloud.zed.dev/client/users/connect`、token 刷新机制等。

## credentials_provider (34 行)
**状态**: ✅ 现已覆盖
`CredentialsProvider` trait 定义了凭证存储的抽象接口：
- `read_credentials(url)` → `(username, password_bytes)`
- `write_credentials(url, username, password)`
- `delete_credentials(url)`
Zed 使用系统钥匙串（macOS Keychain / Linux libsecret）存储凭证。开发模式下使用 JSON 文件。

## zed_credentials_provider (181 行)
**状态**: ✅ 现已覆盖
Zed 的凭证提供者实现，已在前面的分析中完整覆盖：
- **生产模式**: 使用系统 keychain（macOS Keychain, Linux libsecret）
- **开发模式**: 使用 `~/.config/zed/development_credentials` JSON 文件
- Dev channel 自动使用开发模式，除非设置 `ZED_DEVELOPMENT_USE_KEYCHAIN=true`

## language_models_cloud (1,147 行)
**状态**: ✅ 已在分析中完整覆盖
Cloud LLM Provider 的核心实现，已在 `ai-protocol-analysis.md` 和 `language_models_cloud` 报告中详细分析。包含 LLM completion 的完整转发逻辑、Token 认证、流式响应处理。

## language_model (2,149 行)
**状态**: ✅ 已在分析中完整覆盖
`LanguageModel` trait 定义和 `LanguageModelRegistry`，是 AI 通信协议的核心抽象层。

## llama_cpp (911 行)
**状态**: ✅ 现已覆盖
Zed 支持通过 `llama.cpp` 运行本地开源模型（如 Llama、Mistral 等）。
- 端点：`http://localhost:8080/completion`（兼容 llama.cpp 格式）
- 无认证（本地）
- 支持流式和非流式调用
- 不涉及网络协议，不影响反向代理方案

## cloud_api_types 剩余模块
- `plan.rs` — Plan 类型（ZedFree/ZedPro/ZedProTrial/ZedBusiness/ZedStudent）— 已覆盖
- `timestamp.rs` — RFC3339 时间戳序列化
- `websocket_protocol.rs` — WebSocket CBOR 消息（`MessageToClient::UserUpdated`）— 已覆盖