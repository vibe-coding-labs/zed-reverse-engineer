# 循环分析报告 #52 — Agent 数据库层 (Agent DB)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/db.rs` (1,098 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Agent 数据库层管理线程的持久化存储，使用 SQLite/kvp 后端。

## 核心数据结构

```rust
pub struct DbThread {
    pub title: SharedString,                    // 线程标题
    pub messages: Vec<Arc<DbMessage>>,          // 消息历史
    pub updated_at: DateTime<Utc>,              // 最后更新时间
    pub detailed_summary: Option<SharedString>,  // 线程摘要
    pub initial_project_snapshot: Option<Arc<ProjectSnapshot>>, // 项目快照
    pub cumulative_token_usage: TokenUsage,     // 累计 Token 用量
    pub request_token_usage: HashMap<UserMessageId, TokenUsage>, // 每次请求的 Token 用量
    pub model: Option<DbLanguageModel>,         // 使用的模型
    pub profile: Option<AgentProfileId>,        // Agent 配置文件
    pub subagent_context: Option<SubagentContext>, // 子 Agent 上下文
    pub sandboxed_terminal_temp_dir: Option<PathBuf>, // 沙箱临时目录
    // ... 更多字段
}
```

## 数据类型

支持多种序列化格式：
- `Json` — 标准 JSON 序列化
- `Markdown` — 可读性导出
- `Bytes` — 二进制序列化（用于高效存储）

## 数据格式版本

```rust
pub enum DataType {
    DbThread,       // 当前版本
    DbThreadV1,     // 旧版本（迁移支持）
    DbMessage,      // 当前版本
    DbMessageV1,    // 旧版本
}
```

## 计费数据

Agent 持久化了 `cumulative_token_usage` 和 `per-request_token_usage`，这证实了 Zed 会在本地跟踪 LLM Token 消耗，用于计费展示。

## 关键文件

- `crates/agent/src/db.rs` — 数据库层实现