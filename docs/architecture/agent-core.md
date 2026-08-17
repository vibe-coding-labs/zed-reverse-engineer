---
title: Agent 核心设计（NativeAgent 主循环 + 工具调度）
description: Zed 内置 AI Agent 的主循环、工具执行、权限与沙箱机制深度解析
---

# Agent 核心设计 —— Thread 主循环与工具调度

> **源码证据**: `/tmp/zed-src/zed-full/crates/agent/src/thread.rs`（8,739 行）、`agent.rs`（6,935 行）

---

## 一、核心概念：`Thread` 承载一切

Zed 的 AI Agent 核心不是 `NativeAgent`，而是 **`Thread`**（线程/session）。`agent.rs` 里的 `NativeAgent` 更多是"外壳"（管理模型列表、技能扫描、session 存储），真正的 LLM 请求-工具-响应循环全在 `Thread` 里。

```
crates/agent/src/thread.rs:1229
pub struct Thread {
    id: acp::SessionId,            // ACP 协议 session ID
    prompt_id: PromptId,
    title: Option<SharedString>,   // 自动生成/用户设置
    messages: Vec<Arc<Message>>,   // 对话历史
    running_turn: Option<RunningTurn>,  // ★ 当前轮次（跨多次 LLM 请求）
    end_turn_at_next_boundary: bool,    // UI "steering" 终止标记
    pending_message: Option<AgentMessage>,
    tools: BTreeMap<SharedString, Arc<dyn AnyAgentTool>>, // ★ 工具注册表
    model: ThreadModel,                 // 当前模型
    summarization_model: Option<...>,   // 压缩摘要用模型
    thinking_enabled: bool,
    speed: Option<Speed>,
    project: Entity<Project>,
    context_server_registry: Entity<ContextServerRegistry>,
    profile_id: AgentProfileId,
    project_context: Entity<ProjectContext>,
    sandbox_grants: Rc<RefCell<ThreadSandboxGrants>>,  // ★ 本轮已授权的沙箱权限
    ...
}
```

**关键洞察**：`running_turn` 是"agent 思考一个用户输入直到给出最终答复"的完整周期，它**跨越多次 LLM completion 调用**（模型连续发工具调用 → 执行 → 回填 → 再请求）。

---

## 二、消息模型

```rust
// crates/agent/src/thread.rs:106
pub enum Message {
    User(UserMessage),
    Agent(AgentMessage),
    Compaction(info),       // 上下文压缩占位
    Resume,                 // 断点续跑标记
    System(SystemMessage),  // 标题生成等
}
```

- `UserMessage`：人类用户输入（`id`, `content`, `sender: User`, 时间戳）
- `AgentMessage`：模型回复（文本、thinking、工具调用 `tool_results` 等）
- `Message::to_request()` 将内部模型转成发给 LLM 的 `LanguageModelRequestMessage`

---

## 三、主循环：`run_turn_internal`

这是整个 Agent 的心脏。**源码位置**: `thread.rs:2715`（run_turn）与 `thread.rs:~2790`（run_turn_internal）。

```rust
async fn run_turn_internal(...) -> Result<()> {
    let mut attempt = 0;
    let mut intent = CompletionIntent::UserPrompt;
    let mut refusal_fallback_model: Option<Arc<dyn LanguageModel>> = None;

    loop {
        // 1. 若上下文超阈值，先自动压缩 (perform_compaction_if_needed)
        // 2. 重新读取模型 + 刷新本轮工具 (refresh_turn_tools)
        // 3. 构建 completion 请求 (build_completion_request)
        let (model, request) = ...;
        let (mut events, mut error) = model.stream_completion(request, cx).await;

        let mut tool_results = FuturesUnordered::new();

        // ---- 事件消费循环（LLM 流式输出 + 工具结果 + 取消信号竞争）----
        loop {
            let first_event = futures::select! {
                event = events.next() => event,
                tool_result = tool_results.next() => { ...收集早到的工具结果... }
                _ = cancellation_rx.changed() => { cancelled = true; break; }
            };
            // 批量处理事件：handle_completion_event
            //   ↳ Text        → 追加文本
            //   ↳ Thinking    → 追加思维
            //   ↳ ToolUse     → handle_tool_use_event 启动工具任务(返回 Task)
            //   ↳ UsageUpdate → 遥测 + token 用量累计
            //   ↳ Stop(Refusal/MaxTokens) → 抛错
        }

        // 4. 释放流(释放并发信号量) → 处理早到工具结果 → 等待所有工具结果
        // 5. 若 end_turn（无工具调用）→ return
        // 6. 否则 intent = ToolResults，回到循环顶部（下一轮带工具结果的请求）
    }
}
```

### 各阶段细节

| 阶段 | 实现 | 说明 |
|------|------|------|
| **压缩** | `perform_compaction_if_needed` | 上下文超过阈值**(可配百分比，默认约 65% 上下文窗口)**自动压缩。用 `summarization_model` 生成摘要插入历史 |
| **构建请求** | `build_completion_request(intent, cx)` | 组装 system prompt + 历史 + 项目上下文 + 工具 schema |
| **流式调用** | `model.stream_completion(request, cx)` | 返回事件流；模型是 `Arc<dyn LanguageModel>` |
| **事件处理** | `handle_completion_event` | 状态机：文本/思考/工具用/用量/停止 |
| **工具调度** | `handle_tool_use_event` → `run_tool` | 校验工具存在 → 检查受限工作区 → 启动工具 Task |
| **回填** | `process_tool_result` | 把工具结果插回 `pending_message.tool_results`，UI 更新 |
| **终止** | `StopReason::EndTurn` | 工具全部完成且无 pending → 发 `send_stop`，`running_turn.take()` |

### CompletionError 处理

```rust
// thread.rs run_turn 的错误分发
Err(CompletionError::Refusal)   → send_stop(Refusal); 还原消息（truncate）
Err(CompletionError::MaxTokens) → send_stop(MaxTokens)
Err(CompletionError::Other)     → send_error(error)
```

模型**拒绝(refusal)时可自动降级**：`refusal_fallback_model` 会查找当前模型的 `refusal_fallback_model_id` 配置，用备用模型重试并发送 `RetryStatus` 到 UI。

### 重试机制

`retry_completion_error`：`LanguageModelCompletionError`（PromptTooLarge / 429 / 5xx 等）→ 查 `retry_strategy_for(&error)` → 计算退避时长 → 等待 → 重试（`attempt` 递增）。

> 注意：走 Zed Cloud (`zed.dev`) 的请求只在用户有 Plan 时自动重试；直连 provider 总是重试。

---

## 四、工具调度架构

### 工具注册表

`Thread.tools` 是 `BTreeMap<共享名, Arc<dyn AnyAgentTool>>`，在**每次 turn 开始时**由 `enabled_tools(cx)` 构建（`refresh_turn_tools` 每轮刷新，让 mid-turn 的配置变化生效）。

```rust
// thread.rs:4109
fn enabled_tools(&self, cx: &App) -> BTreeMap<SharedString, Arc<dyn AnyAgentTool>> {
    // - 注册所有 AgentTool 实现（read_file/write_file/...）
    // - 按 feature flag 过滤（如 LspTool、RenameTool 需 flag）
    // - 加 MCP context_server 工具（context_server_registry）
    // - 受限工作区时过滤 allow_in_restricted_mode()==false 的工具
}
```

### 工具调用生命周期

```
LLM 输出 ToolUse
  → handle_tool_use_event:
      ├─ 校验工具存在（不存在→错误 tool result）
      ├─ 校验输入 JSON（解析失败→错误 tool result）
      ├─ 若 is_input_complete=false 且工具支持流式输入：
      │     → 放进 running_turn.streaming_tool_inputs（边流边积累参数）
      └─ 完整输入 → run_tool(...)
  → run_tool:
      ├─ 检查 allow_in_restricted_mode（受限工作区拒绝）
      ├─ 创建 ToolCallEventStream（含 sandbox_grants + cancellation）
      ├─ update_fields(status: InProgress)
      ├─ tool.run(input, event_stream, cx)   ← 真正执行
      └─ foreground_executor 等待 → 返回 (owning_message_ix, ToolResult)
  → process_tool_result: 写回 pending_message，UI 更新状态/错误
```

### 并行工具调用

`tool_results: FuturesUnordered<Task<...>>` 支持**并发执行多个工具**；模型可以同时产生多个 `tool_use` 块。`early_tool_results` 处理"流式输入还没发完但工具已报错"的窗口问题，错误且仍在流式输入的工具会中断主循环。

---

## 五、权限与确认（关键安全机制）

工具在执行中通过 `ToolCallEventStream.authorize(...)` 请求授权，最终落到 `Thread::authorize` → `run_authorization_loop`。决策由 **`ToolPermissionDecision`** 给出：

```rust
// crates/agent/src/tool_permissions.rs:208
pub enum ToolPermissionDecision {
    Allow,
    Deny(String),
    Confirm,    // 需要弹窗问用户
}
```

### 决策优先级（源码注释原文提炼）

```
1. 硬编码安全规则（如阻止 `rm -rf /`）——任何设置都无法覆盖
2. always_deny 模式  → 直接拒绝（优先于其他）
3. always_confirm    → 弹窗确认
4. always_allow      → 直接放行
5. 工具级 default    → ToolPermissionMode::{Allow,Deny,Confirm}
6. 全局 default      → tool_permissions.default
```

### 授权弹窗选项（PermissionOptions）

- **Flat**：一次性选项（Allow once / Deny once）
- **Dropdown**(each with allow+deny)：授权带"记住"语义：
  - `always_allow_mcp:{tool_id}` / `always_deny_mcp:{tool_id}`（对 MCP 工具的"总是"）
  - `allow`/`deny`（仅本次）
  - 模式化授权：`DropdownWithPatterns`（如终端命令 `git push` 一直允许）
- 每个授权请求附带 `allow_similar_permissions` / meta（如命令类别）

### 授权类型（`authorize_*` 系列）

| 方法 | 场景 |
|------|------|
| `authorize_third_party_tool` | MCP/外部工具 |
| `authorize` | 通用 file/命令授权 |
| `authorize_always_prompt` | 强制每次询问 |
| `authorize_sandbox` | 沙箱内命令的沙箱授权 |
| `authorize_sandbox_fallback` | 沙箱不可用时的回退确认 |
| `authorize_windows_fs_warning` | Windows 文件系统警告 |
| `authorize_dirty_buffer` | 覆盖有未保存内容的 buffer |

### 线程级授权记忆

`sandbox_grants: Rc<RefCell<ThreadSandboxGrants>>`：用户在某线程内批准过"允许/拒绝"的权限会被缓存，**同线程后续相同请求跳过弹窗**。它不会持久化（重启丢失）。

---

## 六、沙箱（OS 级隔离）

```rust
// crates/agent/src/sandboxing.rs:95
pub enum ThreadSandbox {
    Unsandboxed,                          // 无沙箱，默认（feature flag 关闭）
    Sandboxed(SandboxPolicy),             // 有 OS 沙箱
}
```

- **平台集成**：macOS → Seatbelt，Linux → Bubblewrap，Windows → Bubblewrap(WSL)
- **开启条件**：`sandboxing` feature flag + 本地项目 + 平台有实现 + 未持久 `allow_unsandboxed`
- **策略**：写入支持 `worktree 根目录`；保护 `.git` 目录（含 linked worktree 的 common dir）
- **合并**：`merge()` 按白名单语义叠加（settings 沙箱 ∥ 线程 grants）
- **模型逃生口**：`unsandboxed: true` 单次/整线程批准后，该命令不套沙箱，但**工具集和 prompt 不变**（`sandboxed_terminal` 工具仍暴露）

---

## 七、中止与恢复

`Thread::cancel`（thread.rs:2256）：

```
cancel()
  → running_turn 的 Task 被 drop（ToolCallEventStream 收到取消信号）
  → 运行中的工具如果支持取消会停掉
  → was_cancelled 标记避免清理触碰新 turn
```

**steering**：UI 在 agent 运行中途插入新消息时设置 `end_turn_at_next_boundary = true`，当前轮在下一个消息边界结束，不强行打断工具执行。

---

## 八、与模型层的接口

`Thread` 依赖 `language_model` 抽象，不直接碰具体 provider：

```rust
// language_model::LanguageModel
trait LanguageModel {
    fn id / provider_id / name
    fn stream_completion(request, cx) -> Task<Result<LanguageModelEventStream>>
    fn responds_to(...) / supports_tools() / supports_images() / supports_thinking()
    fn refusal_fallback_model_id() -> Option<...>
}
```

provider 有：Anthropic / OpenAI / Google / xAI / Ollama / LM Studio / Mistral / OpenRouter / **zed.dev(cloud_llm_client)** 等。`LanguageModelRegistry` 全局注册、`select_default_model` 决定默认。

---

## 九、状态事件（对 UI 的广播）

`ThreadEvent` 通过 `ThreadEventStream`（unbounded mpsc）发送：

- `MessageAdded / MessageRemoved`
- `ToolCallStarted / ToolCallUpdated / ToolCallFinished`
- `Stop(StopReason)` / `Error` / `Retry` / `Compaction`
- `SandboxStatusChanged`

UI（`agent_ui`）订阅这些事件驱动面板更新。所有事件都通过 `cx.notify()` 触发 GPUI 重绘。

---

## 参考

- `crates/agent/src/thread.rs` — 主循环/工具/权限核心
- `crates/agent/src/tool_permissions.rs` — 权限决策链
- `crates/agent/src/sandboxing.rs` — 沙箱策略
- `crates/agent/src/agent.rs` — NativeAgent 外壳
- 下一篇：[Agent 工具系统设计](agent-tools.md)