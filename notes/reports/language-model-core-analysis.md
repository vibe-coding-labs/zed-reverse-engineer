# 分析报告 — language_model_core (语言模型核心类型)

**源码位置**: `crates/language_model_core/src/` (2,319 行)
**分析前状态**: ❌ 部分了解接口，未完整分析

## 概述

`language_model_core` 是所有 LLM 交互的基础 crate，定义了语言模型调用、工具调用、角色等核心类型。

## 核心模块

| 模块 | 行数 | 说明 |
|------|------|------|
| `tool_schema.rs` | 844 | 工具调用 Schema（JSON Schema → LLM Tool） |
| `language_model_core.rs` | 662 | 核心类型（CompletionEvent、Request、Role） |
| `request.rs` | 574 | 请求构建 |
| `rate_limiter.rs` | — | 请求限流 |
| `role.rs` | — | 角色枚举 |
| `provider.rs` | — | Provider ID/Name 常量 |
| `util.rs` | 111 | 工具函数 |

## 核心类型

```rust
// 请求
pub struct LanguageModelRequest {
    pub messages: Vec<LanguageModelRequestMessage>,
    pub tools: Option<Vec<LanguageModelRequestTool>>,
    pub tool_choice: LanguageModelToolChoice,
    pub temperature: Option<f32>,
    pub stop: Vec<String>,
    pub max_tokens: u64,
    pub thinking: Option<ThinkingConfig>,
}

// 响应事件
pub enum LanguageModelCompletionEvent {
    StartMessage { message_id: String },
    Text(String),
    Thinking { thinking: String, signature: Option<String> },
    ToolUse(LanguageModelToolUse),
    Stop(LanguageModelStopReason),
    UsageUpdate(TokenUsage),
}

// Provider ID 常量
pub const ZED_CLOUD_PROVIDER_ID: LanguageModelProviderId = LanguageModelProviderId::new("zed.dev");
pub const ANTHROPIC_PROVIDER_ID: LanguageModelProviderId = LanguageModelProviderId::new("anthropic");
pub const OPEN_AI_PROVIDER_ID: LanguageModelProviderId = LanguageModelProviderId::new("open_ai");
pub const GOOGLE_PROVIDER_ID: LanguageModelProviderId = LanguageModelProviderId::new("google");
pub const X_AI_PROVIDER_ID: LanguageModelProviderId = LanguageModelProviderId::new("x_ai");
```

## 工具调用 Schema

`tool_schema.rs` 实现了将工具定义转换为 LLM 可识别的 JSON Schema 格式。所有 Agent 工具（ReadFileTool、EditFileTool 等）的 `input_schema` 通过此模块生成。

## Provider 常量

| 常量 | 值 | 说明 |
|------|-----|------|
| `ZED_CLOUD_PROVIDER_ID` | `"zed.dev"` | Zed 托管 LLM |
| `ZED_CLOUD_PROVIDER_NAME` | `"Zed"` | 显示名称 |
| `ANTHROPIC_PROVIDER_ID` | `"anthropic"` | Anthropic Claude |
| `OPEN_AI_PROVIDER_ID` | `"open_ai"` | OpenAI |
| `GOOGLE_PROVIDER_ID` | `"google"` | Google Gemini |
| `X_AI_PROVIDER_ID` | `"x_ai"` | xAI Grok |

## 限流

`rate_limiter.rs` 实现请求限流，为 CloudLanguageModel 提供 4 并发限制。

## 关键文件

- `crates/language_model_core/src/language_model_core.rs` — 核心类型
- `crates/language_model_core/src/tool_schema.rs` — 工具 Schema
- `crates/language_model_core/src/request.rs` — 请求构建
- `crates/language_model_core/src/provider.rs` — Provider 常量