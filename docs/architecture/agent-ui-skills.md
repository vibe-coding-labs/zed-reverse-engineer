---
title: Agent UI 面板与技能 (Skills) 系统
description: agent_ui 面板状态机、消息渲染；skills 的目录/格式/加载/权限
---

# Agent UI 面板与技能系统

> **源码证据**: `/tmp/zed-src/zed-full/crates/agent_ui/`（agent_panel.rs 13.5k 行 + conversation_view.rs 11.2k 行）、`crates/agent_skills/agent_skills.rs`（2,187 行）

---

## 一、Agent Panel 架构

`AgentPanel`（`crates/agent_ui/src/agent_panel.rs`）是工作区里的可停靠面板（支持 DockPosition，除 Bottom 外均可）。

### 核心状态

```rust
pub struct AgentPanel {
    workspace_id: Option<WorkspaceId>,   // 数据库键
    user_store / project / fs,           // 依赖实体
    thread_store: Entity<ThreadStore>,   // 会话持久化索引
    connection_store: Entity<AgentConnectionStore>,  // agent 服务器连接
    context_server_registry,
    base_view: BaseView,                 // 触发方式记忆（draft 从哪来）
    draft_thread: Option<Entity<ConversationView>>,        // ★ 新会话草稿
    retained_threads: HashMap<ThreadId, Entity<ConversationView>>,  // ★ 已存在的会话
    terminals: HashMap<TerminalId, AgentTerminal>,   // agent 启动的终端
    zoomed: bool,                        // 面板放大态
    selected_agent: Agent,               // 当前 agent（在 Zed/Claude/Codex...间切换）
    ...
}
```

### 三种可见表面（VisibleSurface）

```
Uninitialized      → 首次打开，冒烟
AgentThread(view)  → 一个 ConversationView（会话内容）
Terminal(view)     → agent 启动的终端
```

面板在「草稿会话」与「已保留会话」间切换，`last_created_entry_kind` 记忆最近起点。

### 事件

```rust
pub enum AgentPanelEvent {
    ActiveViewChanged,
    ActiveViewFocused,
    EntryChanged,
    TerminalCloseRequested { metadata },
    ThreadInteracted { thread_id },   // 用于最近会话排序
}
```

---

## 二、会话视图（ConversationView）

`ConversationView`（1184 行结构，11184 行总）是**单个会话的实体**。既是 UI 也是状态（GPUI Entity）。

### 消息渲染管线

- **markdown 渲染**：`render_agent_markdown`（conversation_view.rs:3452）—— 用项目的高亮/markdown 管线渲染 agent 输出
- **消息种类**：用户消息、agent 文本、thinking 折叠、工具调用卡片（含 diff/终端）、compaction 标记、错误
- **流式更新**：订阅 `ThreadEventStream`（ToolCall 增量、Stop 等）驱动局部刷新

### 输入与提交

- `draft_prompt` 持久化（未发送文本跨会话保留）
- 提交 → `AcpThread::prompt`（见 [ACP 文档](acp-protocol-client.md)）
- 支持 `/` 斜杠命令（含 **skill 调用**）

### 会话并发

`retained_threads` 支持**多个会话同时开着**，每个是独立 ConversationView。面板切换会话 = 切换 VisibleSurface。

---

## 三、Inline Assistant（内联助手）

`inline_assistant.rs`（2,163 行）：在编辑器内选中文本即可触发 AI 助手（不离开编辑视图）：
- 复用同一套 Thread 引擎，只是渲染层是 inline popover
- 支持生成/改写/解释等 inline 意图

`terminal_inline_assistant.rs`：终端内的 AI 助手（解释报错、生成命令）。

---

## 四、Skills 技能系统

### 目录约定

```
~/.agents/skills/<skill-name>/SKILL.md          ← 全局技能（所有项目可用）
<project>/.agents/skills/<skill-name>/SKILL.md  ← 项目本地技能（随仓库走）
嵌入式 builtin：crates/agent_skills/builtin/<name>/SKILL.md   ← 编译进二进制
```

`AGENTS_DIR_NAME = ".agents"`、`SKILLS_DIR_NAME = "skills"`、`SKILL_FILE_NAME = "SKILL.md"`。

### Skill 结构

```rust
pub struct Skill {
    pub name: String,          // 目录名（正则 ^[a-z0-9]+(-[a-z0-9]+)*$，≤64）
    pub description: String,   // 模型决策用信号（≤1024 字节）
    pub source: SkillSource,   // BuiltIn | Global | ProjectLocal{worktree_id,...}
    pub directory_path: PathBuf,   // 技能目录（可带辅助文件）
    pub skill_file_path: PathBuf,  // SKILL.md 绝对路径
    pub load_warnings: Vec<SkillLoadWarning>,
    pub disable_model_invocation: bool,  // 隐藏于模型目录，仅斜杠调用
    pub embedded_body: Option<&'static str>,  // 内置技能内嵌正文
}

pub enum SkillSource {
    BuiltIn,        // 优先级最低（可被覆盖）
    Global,         // ~/.agents/skills/
    ProjectLocal { worktree_id, worktree_root_name },
}

pub struct SkillMetadata { name, description, disable_model_invocation }
pub struct SkillSummary { name, description, location }  // 进 system prompt
```

### SKILL.md 格式

```markdown
---
name: my-skill-name          # 必填，与目录名一致
description: 一句话说明      # 必填 ≤1024，模型判断何时使用
disable-model-invocation: true  # 可选：不进模型目录
---

# 指令正文
（告诉 agent 如何完成该技能；可引用同目录辅助文件如 templates/）
```

前端由 `parse_skill_frontmatter` 解析 + 校验（`validate_name`/`validate_description`）。

### 加载与索引

- **并发上限**：`SKILL_IO_CONCURRENCY = 16`（防上千技能目录打爆 FD）
- **体积限制**：`MAX_SKILL_FILE_SIZE = 100KB`，描述超长产生 `SkillLoadWarning`（非致命）
- **system prompt 注入**：技能描述汇总为 `SkillSummary`，`MAX_SKILL_DESCRIPTIONS_SIZE = 50KB` 封顶 —— 描述过长会拿掉最不相关的，保住 token
- **SkillIndex** 组织已加载技能；`load_skills_from_directory` 遍历目录
- **内建技能**：`builtin_skills(embedded_body)` 直接从二进制 Content 提供正文，无需读盘

### 覆盖优先级

```
ProjectLocal > Global > BuiltIn（同名时高位覆盖低位）
```

### 与工具/权限联动

- `skill` 工具（`skill_tool.rs`）加载技能正文喂给模型（带 `<directory>` 信封标签使模型能引用辅助文件）
- `write_file`/`edit_file` 有**特殊 allow 路径** `~/.agents/skills`（创建编辑技能是社区常见场景）
- `disable_model_invocation` 的技能只能**用户斜杠 `/name` 手动调用**
- 投影技能的信任：project-local 技能需 worktree 已信任（`test_project_skills_require_worktree_trust`）

---

## 五、Agent 注册 & 选择器 UI

- `agent_connection_store.rs`：管理 `AgentConnection` 们的连接与状态（per-project agent 实例）
- `model_selector` / `agent_model_selector` / `profile_selector` / `mode_selector`：下拉选择
- `agent_registry_ui.rs`：用户安装/管理外部 agent（来自 registry）
- `favorite_models.rs`：模型收藏
- `config_options.rs` / `agent_configuration`：按 session 的配置选项 UI

---

## 六、与引擎解耦的关键

**UI 层完全不知道 agent 是内置还是外部 ACP**。`AgentConnectionStore` 持 `Rc<dyn AgentConnection>`，UI 只调用 `prompt/cancel/retry/load_session` 等通用方法。技能也同理 —— `agent_skills` 是叶子 crate（不依赖 worktree），SkillScopeId 只是 usize，由 agent crate 决定怎么用。

---

## 参考

- `crates/agent_ui/src/agent_panel.rs` — 面板与状态机
- `crates/agent_ui/src/conversation_view.rs` — 会话视图
- `crates/agent_ui/src/inline_assistant.rs` / `terminal_inline_assistant.rs` — 内联助手
- `crates/agent_skills/agent_skills.rs` — 技能系统
- `crates/agent_skills/builtin/create-skill/SKILL.md` — 官方技能示例（自举）
- 关联：[ACP 协议客户端](acp-protocol-client.md) · [Agent 工具系统](agent-tools.md)