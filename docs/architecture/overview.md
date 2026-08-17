---
title: Zed 整体架构分层
description: 基于 Zed 官方源码（master）的 243 个 crate 架构全景分析
---

# Zed 整体架构分层

> **分析对象**: [zed-industries/zed](https://github.com/zed-industries/zed) master 分支（`b2d9c2e`，v0.61）
> **规模**: 243 个 workspace crate，约 150 万行 Rust 代码
> **分析基准**: 本地克隆 `/tmp/zed-src/zed-full/`（本仓库分析的源码证据均引用此克隆）

---

## 一、总体视图

Zed 是**单进程多线程的 Rust 桌面应用**。它没有采用经典的 client/server 进程拆分（VSCode 那样），而是把 UI、编辑器、LSP 桥、AI Agent、网络全部塞进一个进程，同时用内部异步 actor 模型（`Entity` + `AsyncApp` + Task）做并发隔离。

```
┌─────────────────────────────────────────────────────────────┐
│                     Zed 应用进程 (crates/zed)                │
│                                                             │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────┐  │
│  │  UI 渲染层     │   │  编辑器核心层   │   │  功能模块层    │  │
│  │  gpui/ui     │   │  editor/rope  │   │  terminal/...  │  │
│  └──────┬────────┘   └──────┬────────┘   └──────┬────────┘  │
│         │                   │                   │           │
│  ┌──────┴───────────────────┴───────────────────┴────────┐  │
│  │                 Workspace 集成层                       │  │
│  │  crates/workspace: 面板、标题栏、快捷键、命令注册        │  │
│  └──────┬───────────────────┬────────────────────────────┘  │
│         │                   │                               │
│  ┌──────┴──────────┐  ┌─────┴──────────┐   ┌──────────────┐ │
│  │ Project/Worktree │  │ Agent 子系统    │   │  云服务客户端 │ │
│  │ 文件树/LSP/任务   │  │ agent/agents   │   │ client/cloud │ │
│  └─────────────────┘  └────────────────┘   └──────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

---

## 二、分层结构（243 个 crate 归类）

### Layer 0 — 基础设施（被最多 crate 依赖的基座）

| crate | 行数(约) | 职责 |
|-------|---------|------|
| `gpui` | 35k+ | GPU 驱动的 UI 框架 + 异步 actor 运行时。**全项目最大的地基**：`Entity`(引用计数的对象句柄)、`AsyncApp`/`Context`(任务上下文)、`App`(全局状态)、事件派发 |
| `settings` | 15k | 全局设置树，`SettingsStore` 承载所有 settable 配置，被任何功能读取 |
| `util` / `collections` | 10k+ | 通用工具：`ResultExt`、`Postcard` 序列化、`HashMap`/`IndexMap` 扩展 |
| `fs` | - | 文件系统抽象（本地/远程统一接口） |
| `telemetry` | - | 遥测埋点（`telemetry::event!` 宏全项目可见） |
| `feature_flags` | - | 功能开关（如 sandboxing、LSP 工具），`FeatureFlagAppExt` |
| `release_channel` | - | Release/Dev 通道决定行为 |
| `sqlez`, `db` | - | SQLite 封装（会话、账号等持久化） |

### Layer 1 — 编辑器核心（文档模型 + 渲染）

| crate | 行数(约) | 职责 |
|-------|---------|------|
| `rope` | 4k | 文本核心数据结构（B-tree 变体 rope） |
| `sum_tree` | 3k | 区间求和树（行偏移量计算） |
| `text` | - | 文档/点/Patch 类型 |
| `language` | 40k | 编程语言抽象：语法树、`LanguageRegistry`、语法高亮 |
| `language_core` | - | `Point`、`Range` 等编辑器坐标类型 |
| `editor` | 100k+ | **最大核心 crate**：`Editor`(122k 行总)、多 Buffer 渲染、光标、输入组合、多游标 |
| `multi_buffer` | 16k | Excerpt(片段) 拼接多 buffer 视图（搜索/诊断面板） |
| `project` | 100k+ | `Project`/`Worktree` 建模、文件监听、git 集成、`LspStore`、任务、进程序列化 |
| `worktree` | 25k | 物理目录树快照与同步 |

### Layer 2 — UI/桌面壳（gpui 之上的应用 UI）

| crate | 职责 |
|-------|------|
| `ui` / `ui_input` / `ui_macros` / `ui_prompt` | 应用级控件库（按钮/输入/弹窗） |
| `theme` / `theme_settings` / `theme_importer` | 主题体系 |
| `workspace` | 主工作区：面板布局、标签页、`Workspace` 命令中心 |
| `sidebar` / `project_panel` / `outline_panel` / `search` | 侧边栏与面板 |
| `title_bar` / `menu` / `command_palette` / `feedback` | 桌面壳元素 |
| `gpui_macos`/`gpui_linux`/`gpui_windows`/`gpui_web`/`gpui_wgpu` | GPU 平台后端 |
| `dap` / `debugger_ui` / `debugger_tools` | 调试器 |

### Layer 3 — 功能模块（业务功能）

| 模块 | crate | 职责 |
|------|-------|------|
| 终端 | `terminal`, `terminal_view` | 内置终端（`TerminalBuilder`、`SpawnInTerminal`） |
| 任务 | `task`, `tasks_ui` | 任务运行器（`ShellBuilder`） |
| Vim | `vim`, `vim_mode_setting` | Vim 模式 |
| 版本控制 | `git`, `git_ui` | Git 集成、Hunk 视图 |
| 协作 | `collab`, `collab_ui`, `channel`, `call`, `livekit_*` | 多人实时协作（Collab RPC + LiveKit 音视频） |
| 搜索/替换 | `search` | 跨文件搜索 |
| 扩展 | `extension`, `extension_host`, `extension_api`, `extension_cli` | 插件系统（WASM 宿主） |
| 语言服务 | `lsp`, `language_tools` | LSP 客户端协议 |
| 变量/图表 | `csv_preview`, `image_viewer`, `markdown_preview`, `mermaid_render`, `svg_preview` | 可视化预览 |

### Layer 4 — AI/Agent 子系统（本仓库重点）

| crate | 行数(约) | 职责 |
|-------|---------|------|
| `agent` | 70k | **内置 AI Agent**：`NativeAgent`+`Thread`+工具注册表+会话持久化 |
| `agent_servers` | 20k | **Agent 服务器抽象**：`AgentServer` trait、ACP 外部进程适配器 |
| `acp_thread` / `acp_tools` | 15k | ACP 会话线程管理、外部 Agent 封装 |
| `agent_ui` | 30k | Agent 面板 UI（`agent_panel` 13.5k 行） |
| `agent_settings` / `agent_skills` / `agent_servers` | - | 配置 / 技能 (skills) / 服务器目录 |
| `language_model` | 10k+ | **LLM 抽象层**：`LanguageModel`/`LanguageModelProvider`/`LanguageModelRegistry` |
| `language_models` | - | 各 provider 的注册表（Anthropic/OpenAI/Google/xAI/...） |
| `language_models_cloud` | 1.1k | 走 `cloud.zed.dev` 代理的 LLM provider |
| `cloud_llm_client` / `cloud_api_client` / `cloud_api_types` | 2k | Zed Cloud API 客户端与类型（详见协议文档） |
| `openai` / `anthropic` / `google_ai` / `x_ai` / `bedrock` / `copilot` / `deepseek` / `mistral` / `ollama` / `lmstudio` / `open_router` / `openai_subscribed` | - | 各家模型 provider 直连适配 |
| `edit_prediction` | 15k | Zeta2 编辑预测引擎（补全） |
| `prompt_store` | - | 提示词管理 |
| `context_server` | - | MCP 上下文服务器 |

### Layer 5 — 网络与云服务

| crate | 职责 |
|-------|------|
| `client` | Collab WebSocket 客户端（RPC 连接） |
| `rpc` / `proto` | RPC 协议与 protobuf 定义（版本 v68） |
| `http_client` / `reqwest_client` / `aws_http_client` | HTTP 客户端封装 |
| `http_proxy` | 代理配置 |
| `oauth_callback_server` | OAuth 回调本地服务器 |
| `zed_credentials_provider` / `credentials_provider` | 凭证存取（keychain/libsecret/文件） |
| `proxy_handshake` | Connan 代理握手 |

### Layer 6 — 外部集成

- `node_runtime`：Node/WASM 运行时（扩展宿主）
- `livekit_api`/`livekit_client`：实时音视频
- `web_search`：网络搜索 provider 抽象
- `git_hosting_providers`：GitHub/GitLab 托管集成
- `dev_container`：开发容器
- `remote`/`remote_connection`：远程开发
- `vim`：Vim 模拟层

---

## 三、核心抽象与数据流

### 1. GPUI 的对象模型：`Entity<T>`

Zed 不直接持有对象引用，而是全部用 `Entity<T>`（内部是 `Rc`/`Weak` 封装的引用计数句柄）。所有状态变更须在 `Context<T>`（`ctx.update(...)`）内执行，这保证了：

- **单线程主循环化**：UI 逻辑都在主线程上，通过 `cx.update` 调度
- **WeakEntity 跨任务安全**：异步任务中持有 `WeakEntity` 避免循环引用
- **EventEmitter**：`Thread`、`Editor` 等都实现 `EventEmitter<'static>`，通过 `Subscription` 广播状态变化

```rust
// crates/agent/src/native_agent_server.rs
let agent = cx.update(|cx| NativeAgent::new(thread_store, templates, fs, cx));
```

### 2. 消息总线：命令 + 订阅

- **命令**(`Action`)：全局注册 `workspace::command`，键盘绑定通过 keymap
- **订阅**(`Subscription`)：`cx.subscribe(&entity, |this, emitter, event, cx| ...)` 实现事件驱动

### 3. 一条按键的旅程

```
键盘中断 → gpui key_dispatch → 命令查找(keymap) → Editor 处理 → buffer 修改
→ language 语法树增量更新 → multi_buffer excerpt 更新 → 渲染(scene) → GPU 帧
```

### 4. 一次 Agent LLM 调用的旅程

```
用户在 Agent 面板输入 → Thread::push_user_message → run_turn()
→ run_turn_internal 循环: build_completion_request → model.stream_completion(request)
→ 收到事件: handle_completion_event (文本/工具调用/压缩请求)
→ 工具调用: 权限检查(require_permissions/ToolPermissionDecision)
→ 工具执行(run on AsyncApp) → 结果回填 → 下一轮工具结果请求
→ 直至 StopReason::EndTurn → 面板更新
```

> 详细主循环见 [Agent 核心设计](agent-core.md)。

---

## 四、关键设计模式总结

1. **一切皆 Entity**：状态对象都用 `Entity<T>` 包装并通过 `Context` 操作，杜绝裸 `Rc` 竞态。
2. **单进程，无 IPC**：与 VSCode（前端/后端进程分离）不同，Zed 把 UI 和逻辑放同一进程，用跨平台 `gpui_platform` 抽象 OS。
3. **Provider 插件化**：LLM provider、搜索 provider、LSP 都是 trait + 注册表模式，`LanguageModelRegistry::global(cx)` 动态装配。
4. **本地优先 + 云可选**：核心编辑器完全不依赖网络；AI 能力既可直接连 Anthropic/OpenAI 等，也可走 Zed Cloud 代理。
5. **异步任务贯穿**：`cx.spawn` 生成的任务在 foreground executor 上执行，`BackgroundExecutor` 做昂贵计算。
6. **强安全模型**：Agent 工具执行有完整权限分级（见 [工具系统](agent-tools.md)）+ 可选 OS 沙箱（macOS Seatbelt / Linux Bubblewrap）。

---

## 五、从依赖关系看"基座"crate

按被依赖的广度，这几个 crate 是全项目的根基（几乎所有功能 crate 都依赖它们）：

```
gpui (UI+运行时)  >  settings (配置)  >  util/collections (工具)  >  fs (文件)  >  language (文本)
```

而 `zed`（主入口 crate）负责把所有部分**装配**到一起，是一个很薄的"胶水层"。

---

## 参考

- 本地源码克隆：`/tmp/zed-src/zed-full/`（master `b2d9c2e`）
- 相关文档：[AI 通信协议](../protocol/ai-protocol.md) · [Agent 核心设计](agent-core.md) · [Agent 工具系统](agent-tools.md) · [ACP 与服务端](agent-servers.md)