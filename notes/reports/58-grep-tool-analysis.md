# 循环分析报告 #58 — Agent 正则搜索工具 (GrepTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/grep_tool.rs` (1,210 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`GrepTool` 是 Agent 的正则搜索工具，支持在项目文件中搜索内容。

## 输入参数

```rust
pub struct GrepToolInput {
    pub regex: String,                     // 正则表达式
    pub include_pattern: Option<String>,   // 文件过滤（glob）
    pub offset: u32,                       // 分页偏移
    pub case_sensitive: bool,              // 是否区分大小写
}
```

## 主要特性

- **正则搜索**：使用 Rust `regex` crate 解析
- **文件过滤**：支持 glob 模式（如 `**/*.rs`、`backend/**/*.ts`）
- **分页**：每页 20 条结果
- **路径优先**：搜索文件**内容**，不能用于搜索文件路径（用 `FindPathTool`）
- **预览**：显示匹配行及上下文的代码片段

## 关键文件

- `crates/agent/src/tools/grep_tool.rs` — 搜索工具实现