---
title: Agent 会话持久化与恢复
description: Thread 的 SQLite 持久化：schema、序列化、保存时机、恢复流程
---

# Agent 会话持久化与恢复

> **源码证据**: `/tmp/zed-src/zed-full/crates/agent/src/db.rs`（1,249 行）、`thread_store.rs`（314 行）、`agent.rs` 的 `save_thread`/`flush_threads_on_quit`、`thread.rs` 的 `to_db`/`from_db`

---

## 一、存储架构概览

Zed 把 Agent 会话持久化为**单表 SQLite key-value**：每个 Thread = 一行，完整的会话（所有消息+元数据）序列化成一个压缩 BLOB。

```
Storage 层
├── ThreadStore (thread_store.rs)   —— 内存中的会话元数据索引 + 全局单例
│     └─ threads: Vec<DbThreadMetadata>   ← 侧边栏会话列表的唯一数据源
├── ThreadsDatabase (db.rs)         —— SQLite 封装
│     └─ threads 表 (id, parent_id, folder_paths, folder_paths_order,
│                   summary, updated_at, data_type, data, created_at)
│     └─ connect: 按 platform/lifecycle 打开 db
└── NativeAgent (agent.rs)          —— 保存/加载/关闭会话的调度者
      └─ sessions: HashMap<SessionId, Session>
```

---

## 二、数据库 Schema

### threads 表

```sql
CREATE TABLE IF NOT EXISTS threads (
    id               TEXT PRIMARY KEY,   -- acp::SessionId
    summary          TEXT NOT NULL,      -- 标题（显示在会话列表）
    updated_at       TEXT NOT NULL,      -- RFC3339
    data_type        TEXT NOT NULL,      -- 压缩标记（见下）
    data             BLOB NOT NULL       -- 完整 Thread 快照
);

-- 迁移追加的列
ALTER TABLE threads ADD COLUMN parent_id         TEXT;   -- 子 Agent：父 SessionId
ALTER TABLE threads ADD COLUMN folder_paths       TEXT;   -- 会话所属目录(序列化)
ALTER TABLE threads ADD COLUMN folder_paths_order TEXT;
ALTER TABLE threads ADD COLUMN created_at         TEXT;
```

### data_type（zstd 压缩）

```rust
const COMPRESSION_LEVEL: i32 = 3;
// data = zstd::encode_all(json_bytes, 3)
// data_type = DataType::Zstd
```

完整流程：`DbThread → serde_json::to_string → zstd level3 → BLOB 入库`。Upsert 语义（`ON CONFLICT(id) DO UPDATE`）。

---

## 三、DbThread 序列化结构

**源码**: `db.rs:54`

```rust
pub struct DbThread {
    title: SharedString,
    messages: Vec<Arc<DbMessage>>,        // 完整对话（DbMessage = crate::Message）
    updated_at: DateTime<Utc>,
    detailed_summary: Option<SharedString>,  // 压缩摘要
    initial_project_snapshot: Option<Arc<ProjectSnapshot>>,  // 项目快照（含 git/未保存buffer）
    cumulative_token_usage: TokenUsage,      // 累计 token 统计
    request_token_usage: HashMap<ClientUserMessageId, TokenUsage>,
    model: Option<DbLanguageModel>,          // 序列化的模型（provider_id + id + telemetry）
    profile: Option<AgentProfileId>,         // agent profile
    subagent_context: Option<SubagentContext>, // 子 Agent 归属
    speed: Option<Speed>,
    thinking_enabled: bool,
    thinking_effort: Option<String>,
    draft_prompt: Option<Vec<acp::ContentBlock>>,  // 未发送的草稿
    ui_scroll_position: Option<SerializedScrollPosition>,  // 恢复滚动位置
    sandboxed_terminal_temp_dir: Option<PathBuf>,
    sandbox_grants: DbSandboxGrants,   // ★ 线程级已授权沙箱权限（见下）
}
```

### DbSandboxGrants（线程级授权持久化）

```rust
pub struct DbSandboxGrants {
    write_paths: Vec<GrantedWritePath>, // 每次授权批准时记录规范化(symlink解析)后的目标
    network_hosts: Vec<String>,          // 已授权的网络 host（如 github.com, *.npmjs.org）
    network_any_host: bool,              // 任意 host 授权
    // unsandboxed_* 等逃生授权也在此
}
```

> 这解释了"重启后同一会话的沙箱授权仍然有效"——用户批准过的**"本线程内允许"**会随会话持久化，而不是每次重开都要重问。

---

## 四、保存时机（何时写 DB）

### 1. 关闭会话时（`close_session` → `save_thread`）

`agent.rs:1736` 的 `save_thread`：

```rust
fn save_thread(&mut self, thread, cx) {
    let Some((id, folder_paths, db_thread)) = self.thread_save_payload(session, cx) else {
        return;   // 空线程不保存
    };
    session.pending_save = cx.spawn(async move |_, cx| {
        database.save_thread(id, db_thread, folder_paths).await...
        thread_store.reload(cx);   // 刷新元数据索引
    });
}
```

- `thread_save_payload` 从可见 worktree 收集 `folder_paths` 并抓取当前 `draft_prompt`
- `Thread::to_db` 在 **background executor** 渲染初始项目快照后完成

### 2. 应用退出时（`flush_threads_on_quit`）

`agent.rs:1795` —— 挂在 `cx.on_app_quit`：

```rust
fn flush_threads_on_quit(&mut self, cx) -> impl Future {
    // 对所有非空 session 预先构建 payload
    // 之后 future::join_all(...) 并发写库（避免 async save 来不及完成丢数据）
}
```

---

## 五、恢复流程（加载会话）

### ThreadStore 加载

```rust
// thread_store.rs
ThreadStore::init_global(cx);       // 应用启动注册全局单例
spawn_reload() → database.list_threads() → threads 元数据缓存
  // 过滤：parent_session_id.is_some() 的子 Agent 线程不入列表（避免显示子会话）
```

### Thread::from_db（thread.rs:1715）

反序列化后**不直接重建 `Thread`**，而是:

1. 还原 `DbThread` 各字段
2. `model` 从 `DbLanguageModel` 解析（`model_from_id`，延迟到 provider 注册后再解析——支持"provider 加载较晚/即时有，持久时暂无"）
3. 重新构造 `Thread`，保留 `sandbox_grants`、`thinking_enabled`、`speed` 等全部用户选择
4. 会话以 `LegacyThread`/`Thread` 两种形态存在（兼容老版本 DB），`load_thread` 统一包装

### `to_db`（thread.rs:1881）

```rust
pub fn to_db(&self, cx) -> Task<DbThread> {
    // 同步构造字段（messages.clone() 等）
    // 异步 background 完成 initial_project_snapshot（抓 git 状态 + 未保存buffer）
}
```

---

## 六、与 ACP SessionList 的桥接

`DbThreadMetadata → AgentSessionInfo`：

```rust
impl From<&DbThreadMetadata> for acp_thread::AgentSessionInfo {
    fn from(meta: &DbThreadMetadata) -> Self {
        Self {
            session_id, work_dirs: Some(folder_paths), title,
            updated_at, created_at, meta: None,
        }
    }
}
```

也就是**内置 NativeAgent 的会话历史通过 `AgentSessionList` 暴露给 ACP 语义的 UI**（session 列表/加载/删除），与外部 agent 的历史完全同构。

---

## 七、设计要点总结

| 点 | 设计 |
|----|------|
| **单表 key-value** | 避免复杂关系 schema；Thread 自包含，恢复 = 反序列化整个 BLOB |
| **压缩** | zstd level 3（追求速度，会话通常 < 几 MB） |
| **版本化** | `version` 字段嵌入序列化数据，支持未来格式迁移 |
| **元数据列 vs BLOB** | `title/summary/updated_at/folder_paths` 冗余到列，供 `list_threads`/排序/分组用，避免反序列化全量 BLOB |
| **异步安全** | 写库都在后台 executor；`pending_save` 去重；关机时 join_all 并发 flush 防丢 |
| **子 Agent 过滤** | `parent_id` 存在的不进会话列表 |
| **沙箱授权持久化** | `DbSandboxGrants` 跟随会话存，重开会话权限不变 |
| **用户状态完整保留** | model/profile/speed/thinking/draft_prompt/滚动位置全保存 |

---

## 参考

- `crates/agent/src/db.rs` — SQLite + 序列化
- `crates/agent/src/thread_store.rs` — 元数据索引
- `crates/agent/src/agent.rs:1736/1795/2123` — 保存/刷新/加载
- `crates/agent/src/thread.rs:1715/1881` — DbThread <-> Thread
- 关联：[Agent 核心设计](agent-core.md) · [ACP 与外部 Agent](agent-servers.md)