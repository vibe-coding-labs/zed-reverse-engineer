# 循环分析报告 #53 — Agent 旧版线程兼容 (Legacy Thread)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/legacy_thread.rs` (396 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`legacy_thread.rs` 提供从旧版线程格式到新版 `DbThread` 的迁移支持。

## 核心功能

```rust
pub struct SerializedThread {
    pub id: String,
    pub title: String,
    pub messages: Vec<SerializedMessage>,
    pub summary: Option<String>,
    pub updated_at: DateTime<Utc>,
}

pub struct SerializedMessage {
    pub id: usize,
    pub role: String,        // "user" | "assistant" | "system"
    pub content: String,
    pub segments: Vec<SerializedMessageSegment>,
    pub tool_calls: Vec<SerializedToolUse>,
    pub edited: bool,
}
```

## 版本升级路径

```rust
// 旧版 V0.1.0 → 新版
pub struct SerializedThreadV0_1_0(serde_json::Value);
impl SerializedThreadV0_1_0 {
    pub fn upgrade(self) -> SerializedThread { ... }
}
```

## 迁移流程

旧版序列化格式（`V0.1.0`）通过 `upgrade()` 方法转换为当前 `SerializedThread` 格式，再转换为 `DbThread`。

## 关键文件

- `crates/agent/src/legacy_thread.rs` — 旧版线程数据和升级逻辑