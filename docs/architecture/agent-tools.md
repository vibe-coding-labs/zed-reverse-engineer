---
title: Agent 工具系统设计（注册 / Schema / 执行 / 撤销 / 权限）
description: Zed Agent 全部工具的 trait 契约、分类、核心工具深度解析
---

# Agent 工具系统设计

> **源码证据**: `/tmp/zed-src/zed-full/crates/agent/src/tools.rs` / `tools/`（33 个文件，约 23k 行）

---

## 一、统一契约：`AgentTool` trait

所有 Agent 工具（内置 + MCP）都实现同一个 trait。**源码位置**: `crates/agent/src/thread.rs:5068`

```rust
pub trait AgentTool
where Self: 'static + Sized
{
    type Input: Deserialize + Serialize + JsonSchema;        // 参数，自动生成 JSON Schema
    type Output: Deserialize + Serialize + Into<LanguageModelToolResultContent>;

    const NAME: &'static str;                                // 工具名（暴露给模型）

    fn description() -> SharedString;                        // 从 Input schema 的 description 字段取
    fn kind() -> acp::ToolKind;                              // Read/Edit/Execute/Other(分类)
    fn initial_title(...) -> SharedString;                   // UI 初始标题（可用部分输入渲染）
    fn input_schema(format) -> Schema;                       // JSON Schema，支持不同格式化
    fn supports_input_streaming() -> bool;                   // 是否支持"边生成边喂参数"
    fn supports_provider(provider_id) -> bool;               // 是否可在某 provider 下暴露
    fn allow_in_restricted_mode() -> bool;                   // 受限工作区是否可见
    fn run(self, input: ToolInput<Input>, event_stream: ToolCallEventStream, cx)
        -> Task<Result<Output, Output>>;                     // ★ 执行入口
}
```

### 关键设计点

1. **错误作为 Output 返回**而非抛异常：`Result<Output, Output>` —— 工具失败信息会被结构化地回传给模型（模型能读到错误文本继续修正），而不是变成 `anyhow::Error`。
2. **`ToolInput` 是流式信道**：支持 `send_partial`（流式参数）与 `send_full`（最终参数）。
3. **`ToolCallEventStream`**：每个工具调用独立的工具事件流，承载**授权、沙箱、diff、输出、取消**等全部运行时交互。

---

## 二、工具全集（分类）

### 文件操作类

| 工具名 | kind | 说明 |
|--------|------|------|
| `read_file` | Read | 读文件（支持 `start_line/end_line` 区间） |
| `write_file` | Edit | 整体写文件（流式输入） |
| `edit_file` | Edit | 流式编辑文件（按字符操作 + 自动缩进） |
| `list_directory` | Read | 列出目录 |
| `find_path` | Read | 按模式找路径 |
| `grep` | Read | 内容搜索 |
| `create_directory` | Edit | 建目录 |
| `delete_path` | Edit | 删除路径 |
| `move_path` | Edit | 移动/重命名路径 |
| `rename_symbol` | Edit | 符号重命名（走 LSP） |
| `copy_path` | Read | 复制路径 |

### 终端 / 系统

| 工具名 | kind | 说明 |
|--------|------|------|
| `terminal` | Execute | 执行 shell 命令（**受限工作区禁用**） |
| `sandboxed_terminal` | Execute | 沙箱内执行命令 |

### 代码智能类（走 LSP）

| 工具名 | kind | 说明 |
|--------|------|------|
| `diagnostics` | Read | 获取诊断信息 |
| `get_code_actions` | Read | 获取 code actions |
| `apply_code_action` | Edit | 应用 code action |
| `go_to_definition` | Read | 跳转定义 |
| `find_references` | Read | 查找引用 |

### Agent / 协作类

| 工具名 | kind | 说明 |
|--------|------|------|
| `spawn_agent` | Other | 生成子 Agent（带 label + context） |
| `create_thread` | Other | 新建线程（feature flag 控制） |
| `list_agents_and_models` | Other | 列出可用 agent 与模型 |
| `skill` | Other | 执行 skill（技能：带 frontmatter 的文档指令集） |

### 网络类

| 工具名 | kind | 说明 |
|--------|------|------|
| `fetch` | Read | 抓取 URL |
| `search_web` | Read | 网络搜索 |

### MCP 集成工具

| 工具名 | kind | 说明 |
|--------|------|------|
| `mcp:{server_id}:{tool_name}` | 动态 | 每个 MCP 服务器暴露的工具，格式见下 |

---

## 三、MCP（Context Server）集成

`ContextServerRegistry`（`crates/agent/src/tools/context_server_registry.rs`）把 MCP 服务器注册进统一工具表：

```rust
// 工具 ID 格式，避免与内置工具冲突
pub fn mcp_tool_id(server_id: &str, tool_name: &str) -> String {
    format!("mcp:{}:{}", server_id, tool_name)
}
```

- 每个 MCP 服务器（`ContextServerStore` 管理其生命周期）的工具和 prompt 在启动时加载
- `tools_for_server()` 迭代注册表输出 `Arc<dyn AnyAgentTool>`
- MCP 工具天然复用同一套授权机制（`authorize_third_party_tool` 提供 `always_allow_mcp:{id}` 选项）
- `ContextServerRegistryEvent::{ToolsChanged, PromptsChanged}` 通知 UI 刷新

---

## 四、写文件 / 编辑文件：流式编辑会话（EditSession）

`write_file` 和 `edit_file` 共用 `EditSession`（`crates/agent/src/tools/edit_session.rs`），是 Zed Agent 编辑能力的核心。

### 流程

```
模型产生 edit_file/write_file 调用
  → EditSessionContext::authorize(path, event_stream, cx)   ← 先权限确认
  → EditSession::new(buffer, old_text, parser, pipeline)
  → event_stream 每次 diff/replace → parser 解析 → apply_char_operations 应用到 buffer
  → 用户实时看到流式编辑
  → compute_new_text_and_diff() → 返回 old_text/new_text/diff
```

### 流式编辑协议

模型输出的不是最终的整个文件，而是**流式的 diff 操作序列**（`WriteEvent`/`EditEvent`），由 `streaming_parser.rs`（1,304 行）解析：

- `EditEvent`: 对已有文本的流式替换指令
- 支持**模糊匹配**（`streaming_fuzzy_matcher.rs` 1,179 行）：模型 diff 的 anchor 不必逐字符精确
- **reindent**（`reindent.rs` 349 行）：编辑后自动重新缩进

### 撤销 / 回滚机制

- `EditSession` 持有 `old_text`（`Arc<String>`）+ `diff: Entity<Diff>`
- `EditSessionOutput::Success { old_text, new_text, diff }` —— UI 用 `Diff` 实体展示增删（绿/红高亮）
- **buffer 级 undo**：编辑器底层 `Buffer::undo` 早就被 Zed 支持，EditSession 依赖 buffer 事务（单个工具 = 一个 buffer 事务），用户按 `cmd+z` 可整体撤销该次工具编辑

### 授权点（重要）

| 授权 | 条件 |
|------|------|
| `authorize_file_edit` | 首次写某路径时 |
| `authorize_dirty_buffer` | 目标 buffer 有未保存修改时（`DirtyBufferDecision::{Save,Discard,Keep}`） |

---

## 五、终端工具：最重的工具

`terminal_tool.rs`（3,816 行），同时有 `terminal`（普通）和 `sandboxed_terminal`（沙箱）两个入口。

### 执行流程

```
TerminalTool::run
  → run_terminal_tool:
       1. working_dir(&input.cd, project) → 解析工作目录（有 worktree escape 防护）
       2. event_stream.authorize(command, context, cx) → 权限确认（先授权后执行）
       3. 沙箱决策（输入 sandbox 字段 + settings.sandbox_permissions）
       4. 创建 terminal（TerminalBuilder / 复用已有终端）
       5. 执行命令，实时流输出给用户
       6. 收集输出 → 回填给模型
```

### 输出限制

- 默认按**字节上限**截断（超出标 `truncated`）：返回 "Command output too long. The first N bytes:..."
- 模型可用 `head_lines` / `tail_lines` **精确控制返回行数**（提示词明确建议不要用 `| head`/`| tail` 绕过）
- 其他终止情况：用户停止 (`user_stopped`)、超时 (`timed_out`)、进程异常退出 (`terminated`)

### 安全防护 (硬编码)

- **拒绝 `rm -rf /` 类命令**（`tool_permissions.rs` 硬规则，`ToolPermissionDecision::Deny` 返回解释）
- 工作目录 `..`/绝对路径逃逸检测
- env 变量扩展注入检测（测试 `test_rejects_variable_expansion`）
- Windows 下 WSL 路径防护

### 沙箱联动

- `sandboxed_terminal` 在 Bubblewrap/Seatbelt 内执行（详见 agent-core 的沙箱章节）
- `sandbox_input` 支持 `allow_fs_write_all`、`unsandboxed`、`allow_all_hosts` 逃生请求 → 需用户批准
- `SandboxRequest`/`effective_sandbox_request` 计算"底线"（settings 已批准的永不缩水）

---

## 六、子 Agent：spawn_agent

`spawn_agent_tool.rs`：允许主 Agent 生成子 Agent 并行执行子任务。

- 复用 `Thread::new_subagent`（继承父 profile、模型选择部分设置）
- 通过 `SiblingThreadHost`/`SubagentHandle` 通信，父 Agent 等待子 Agent `SessionId` 返回
- 子 Agent 完成后结果（摘要）回传给父
- 可级联（子再 spawn），`depth: u8` 限制深度

---

## 七、工具注册与启用逻辑

`Thread::enabled_tools(cx)`（thread.rs:4109）每次 turn 构建工具集：

1. **内置工具全量注册**：上述全部 AgentTool 实现
2. **feature flag 门控**：如 `LspToolFeatureFlag`（控制 LSP 类工具）、`CreateThreadToolFeatureFlag`、`RenameToolFeatureFlag`
3. **provider 兼容过滤**：`supports_provider(&provider_id)` 为 false 的不暴露
4. **受限工作区过滤**：`allow_in_restricted_mode() == false` 的不暴露（含 `terminal`）
5. **MCP 合并**：注册表内所有服务器工具加入

---

## 八、工具与权限/沙箱的完整链路

```
ToolUse 事件
  → handle_tool_use_event (解析/流式分发)
  → run_tool (受限检查 → ToolCallEventStream)
  → tool.run() 内部:
        → event_stream.authorize(..., cx)        → Thread::authorize → 决策(ToolPermissionDecision)
        → event_stream.authorize_sandbox(...)    → 沙箱策略
        → 执行真正的操作
  → output 回填 → process_tool_result → 模型继续
```

授权决策的优先级（硬规则 > always_deny > always_confirm > always_allow > 工具default > 全局default）与线程级授权缓存详见 [Agent 核心设计 · 权限与确认](agent-core.md#五权限与确认关键安全机制)。

---

## 参考

- `crates/agent/src/tools.rs` / `tools/*.rs` — 工具实现
- `crates/agent/src/tools/edit_session.rs` + `edit_session/` — 流式编辑
- `crates/agent/src/tools/context_server_registry.rs` — MCP 集成
- `crates/agent/src/tool_permissions.rs`、`tools/tool_permissions.rs` — 权限决策
- 下一篇：[ACP 协议与外部 Agent 连接](agent-servers.md)