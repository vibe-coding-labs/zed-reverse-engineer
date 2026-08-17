---
title: LLM 抽象层与 Provider 生态
description: LanguageModel/LanguageModelProvider/Registry 三层抽象，20 个 provider 的适配模式
---

# LLM 抽象层与 Provider 生态

> **源码证据**: `/tmp/zed-src/zed-full/crates/language_model/`、`language_model_core/`、`language_models/`

---

## 一、三层抽象总览

Zed 的 AI 能力建立在一个干净的抽象层上，顶层（Agent / Thread）完全不感知具体厂商：

```
┌────────────────────────────────────────────────────────┐
│ 上层消费者: Thread / AcpThread / Agent UI              │
│   只依赖 LanguageModel + LanguageModelRequest         │
├────────────────────────────────────────────────────────┤
│ language_model crate                                  │
│   LanguageModel         (单个模型的能力抽象)           │
│   LanguageModelProvider (厂商/服务商抽象 + 认证)        │
│   LanguageModelRegistry (全局注册表 + 模型选择器)       │
├────────────────────────────────────────────────────────┤
│ language_model_core crate                             │
│   request.rs: LanguageModelRequest / MessageContent /  │
│              LanguageModelCompletionEvent 等核心类型   │
├────────────────────────────────────────────────────────┤
│ language_models crate                                 │
│   provider/*.rs: 20 个具体 provider 实现              │
├────────────────────────────────────────────────────────┤
│ 网络层: anthropic/openai/google_ai/x_ai 等独立 crate   │
│        (各家 API 的 wire 层, 返回 language_model 事件)│
└────────────────────────────────────────────────────────┘
```

---

## 二、`LanguageModel` trait — 单个模型

**源码**: `crates/language_model/src/language_model.rs:65`

```rust
pub trait LanguageModel: Send + Sync {
    // ── 身份 ──
    fn id(&self) -> LanguageModelId;              // "claude-sonnet-4-20250514"
    fn name(&self) -> LanguageModelName;
    fn provider_id(&self) -> LanguageModelProviderId;   // "anthropic"
    fn provider_name(&self) -> LanguageModelProviderName;

    // ── 能力探查（决定系统提示词与 UI 展示）──
    fn is_latest(&self) -> bool;
    fn is_disabled(&self) -> Option<DisabledReason>;
    fn requires_data_retention(&self) -> bool;
    fn refusal_fallback_model_id(&self) -> Option<&'static str>;  // 拒绝时降级模型
    fn supports_thinking(&self) -> bool;
    fn supports_disabling_thinking(&self) -> bool;
    fn supports_fast_mode(&self) -> bool;
    fn supported_effort_levels(&self) -> Vec<LanguageModelEffortLevel>;
    fn supports_server_side_compaction(&self) -> bool;   // 服务端自动压缩
    fn supports_explicit_compaction(&self) -> bool;
    fn supports_images(&self) -> bool;
    fn supports_tools(&self) -> bool;
    fn supports_tool_choice(&self, choice) -> bool;
    fn supports_streaming_tools(&self) -> bool;
    fn supports_split_token_display(&self) -> bool;
    fn tool_input_format(&self) -> LanguageModelToolSchemaFormat;
    fn max_token_count(&self) -> u64;
    fn max_output_tokens(&self) -> Option<u64>;

    // ── 核心调用 ──
    fn stream_completion(request, cx)
        -> BoxFuture<'static, Result<BoxStream<CompletionEvent>, Error>>;
    fn stream_completion_text(request, cx)  // 便捷文本流（自动过滤工具等）
    fn compact(request, cx);                // 显式压缩（支持时）
    fn api_key(&self, cx) -> Option<String>;
    fn model_cost_info(&self) -> Option<LanguageModelCostInfo>;  // 计费信息
}
```

### 设计要点

- **能力自描述**：`supports_*` 系列方法驱动系统提示词构造、UI 开关、上下文压缩策略。例如 Thread 的 `prompt_capabilities()`（agent/thread.rs:1292）直接读 `supports_images()`。
- **拒绝降级**：`refusal_fallback_model_id()` → Thread 在模型拒绝时自动切到备用模型（见 agent-core 文档的 refusal fallback 段）。
- **优雅抽象**：`stream_completion` 返回 `BoxStream<CompletionEvent>`，上层不用关心是 REST 流式还是 SSE。

---

## 三、`LanguageModelProvider` trait — 厂商

**源码**: `crates/language_model/src/language_model.rs:339`

```rust
pub trait LanguageModelProvider: 'static {
    fn id(&self) -> LanguageModelProviderId;
    fn name(&self) -> LanguageModelProviderName;
    fn icon(&self) -> IconOrSvg;
    fn default_model(&self, cx) -> Option<Arc<dyn LanguageModel>>;
    fn default_fast_model(&self, cx) -> Option<Arc<dyn LanguageModel>>;
    fn provided_models(&self, cx) -> Vec<Arc<dyn LanguageModel>>;  // 该厂商全部模型
    fn recommended_models(&self, cx) -> Vec<Arc<dyn LanguageModel>>;
    fn is_authenticated(&self, cx) -> bool;
    fn authenticate(&self, cx) -> Task<Result<(), AuthenticateError>>;
    fn settings_view(&self, cx) -> Option<ProviderSettingsView>;   // 设置 UI
    fn set_api_key(&self, key, cx) -> Task<Result<()>>;
    fn authentication_error_message(&self) -> SharedString;   // 401 提示文案
    fn missing_credentials_error_message(&self) -> SharedString;
}
```

### 认证三种形态

`ProviderSettingsView` 表示 provider 三种设置 UI：

| 变体 | 说明 | 典型 |
|------|------|------|
| `ApiKey(ApiKeyConfiguration)` | 输 API key | Anthropic / OpenAI / xAI / Google |
| `Inline(...)` | 内嵌表单（含 create_view） | Zed Cloud（登录状态） |
| `SubPage(...)` | 子页面 | 部分账号制 provider |

---

## 四、`LanguageModelRegistry` — 全局注册表

**源码**: `crates/language_model/src/registry.rs`

```rust
LanguageModelRegistry::read_global(cx);          // 全局单例读取
LanguageModelRegistry::register_provider<T>(...); // 注册 provider
// 还负责:
//  - load_counted_model_providers()  按计数加载 provider（启用数量限制）
//  - select_default_model()/default_model() 默认模型选择
//  - available_models() 可用模型枚举（供 UI 与 Agent 模型选择器）
```

模型选择是全项目一致的中心状态：Agent 面板的模型下拉、`#agent default_model` 设置、Thread 的 `ThreadModel` 都从 registry 解析。

---

## 五、Provider 实现矩阵（20 个）

分类依据 `language_models/src/provider/*.rs`：

### A. API-Key 直连（独立 crate 处理 wire 层）

| Provider | 文件 | 认证 | 说明 |
|----------|------|------|------|
| Anthropic | `anthropic.rs` | `ANTHROPIC_API_KEY` | 直连 api.anthropic.com（另见 `crates/anthropic/` wire 层） |
| OpenAI | `open_ai.rs` | `OPENAI_API_KEY` | 直连 api.openai.com |
| Google | `google.rs` | `GOOGLE_API_KEY` | generativelanguage API |
| xAI | `x_ai.rs` | `XAI_API_KEY` | 直连 x.ai |

### B. OpenAI-Compatible 模板（`ApiCompatibleProviderState` 基类）

`crates/language_models/src/provider/api_compatible.rs` 提供一个通用基类：读取 `api_url` + `*_API_KEY`，复用同一套实现。

| Provider | 文件 | api_url 特点 |
|----------|------|-------------|
| DeepSeek | `deepseek.rs` | api.deepseek.com |
| LM Studio | `lmstudio.rs` | localhost:1234（本地） |
| Ollama | `ollama.rs` | localhost:11434（本地） |
| Mistral | `mistral.rs` | 兼容 OpenAI 格式 |
| OpenRouter | `open_router.rs` | 聚合网关 |

### C. 专有协议 provider

| Provider | 文件 | 说明 |
|----------|------|------|
| Zed Cloud | `cloud.rs` | ✨ **核心**：走 cloud.zed.dev 代理，详见下节 |
| Bedrock | `bedrock.rs` (3,783 行) | AWS Bedrock 签名认证 |
| Copilot | `copilot_chat.rs` | GitHub Copilot 账号体系 |
| OpenAI Subscribed | `openai_subscribed.rs` | OP 订阅账号 |
| Llama.cpp | `llama_cpp.rs` | 本地 llama-server |
| OpenCode | `opencode.rs` | opencode CLI 工具链 |

### D. 扩展注册（extension.rs）

`language_models/src/extension.rs` 允许**第三方扩展**通过 WASM 注册语言模型 provider —— 这解释了为何 `extension_host` 与 AI 集成。

---

## 六、Zed Cloud provider 深度（与协议文档呼应）

`cloud.rs`（`ZedDotDevAvailableModel`）是把 LLM 请求转发到 `cloud.zed.dev` 的 provider，是**全仓库唯一复用我们逆向协议**的组件：

```rust
// crates/language_models/src/provider/cloud.rs
struct ClientTokenProvider { client, llm_api_token, user_store }
impl CloudLlmTokenProvider for ClientTokenProvider {
    fn auth_context() -> Option<OrganizationId>   // ← 当前组织的 org_id
    fn cached_token(org)  -> cached_llm_token(...) // ← 按 org 缓存
    fn refresh_token(org) -> refresh_llm_token(...)// ← POST /client/llm_tokens
}
```

- **认证上下文 = organization_id**（对应我们逆向的 `/client/llm_tokens` 请求体 `{"organization_id": ...}`）
- **token 缓存/刷新**对应响应头 `x-zed-expired-token` 驱动的刷新机制
- 模型列表来自 `ZedDotDevAvailableModel` 设置（对应 `GET /models`）
- 每 5 分钟 debounce 刷新一次模型列表（`MODELS_REFRESH_DEBOUNCE = 5*60`）

wire 层在 `cloud_llm_client`（`stream_completion` 组装 `POST /completions` 请求）——详见 [AI 通信协议](../protocol/ai-protocol.md)。

---

## 七、请求与响应模型（language_model_core）

`crates/language_model_core/src/request.rs`（696 行）定义与厂商无关的请求/响应：

### LanguageModelRequest

```rust
pub struct LanguageModelRequest {
    thread_id: Option<String>,  prompt_id: Option<String>,
    intent: Option<CompletionIntent>,
    messages: Vec<LanguageModelRequestMessage>,
    tools: Vec<LanguageModelRequestTool>,
    tool_choice: Option<LanguageModelToolChoice>,
    stop: Vec<String>,
    temperature: Option<f32>,
    thinking_allowed: bool,
    thinking_effort: Option<String>,
    speed: Option<Speed>,            // Standard | Fast（fast mode）
    compact_at_tokens: Option<u64>,  // 服务端压缩触发点
}
```

### MessageContent（消息内容联合）

```rust
pub enum MessageContent {
    Text(String),
    Thinking { text, signature },        // 可见思维（Anthropic 风格）
    RedactedThinking(String),            // 加密思维
    Image(LanguageModelImage),
    ToolUse(LanguageModelToolUse),
    ToolResult(LanguageModelToolResult),
    Compaction(CompactedContext),        // 已压缩上下文
}
```

### CompactedContext（压缩上下文）

```rust
pub enum CompactedContext {
    Summary { content, provider_state },  // 摘要（可带 provider 私有状态）
    ProviderState(ProviderCompactionState), // 厂商原生压缩态（如 Anthropic encrypted_content）
}
// ProviderCompactionState { provider_id, format, payload } —— 只有该 provider 能解读
```

这解释了 Thread 的自动化压缩为何能兼容多厂商：**压缩产物以"密封"形式随上下文传递**。

---

## 八、wire 层独立 crate

| crate | 职责 |
|-------|------|
| `crates/anthropic/src/completion.rs` (1,572 行) | Anthropic Messages API 事件解析 → `LanguageModelCompletionEvent` |
| `crates/anthropic/src/batches.rs` | 批量推理 |
| `crates/openai/`、`google_ai/`、`x_ai/` | 同类 |

这些 crate 负责：HTTP 请求构造、SSE/流解析、错误码映射（429→rate limit、401→auth、402→plan 限制）、tool 参数 schema 还原。

---

## 参考

- `crates/language_model/src/language_model.rs` — 双 trait 定义
- `crates/language_model/src/registry.rs` — 注册表
- `crates/language_model_core/src/request.rs` — 核心类型
- `crates/language_models/src/provider/*.rs` — 20 个 provider
- 关联：[AI 通信协议](../protocol/ai-protocol.md) · [Agent 核心设计](agent-core.md)