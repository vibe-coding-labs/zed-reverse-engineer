# 循环分析报告 #32 — 项目搜索系统 (Project Search)

**分析时间**: 2026-07-06
**源码位置**: `crates/search/src/` (10,325 行) + `crates/project/src/project_search.rs`
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 的项目搜索系统支持全文搜索和正则搜索，是 AI Agent 的 `GrepTool` 和 `SearchTool` 的基础。

## 核心类型

```rust
// crates/project/src/project_search.rs
pub struct SearchQuery {
    pub query: String,              // 搜索关键词
    pub regex: bool,                // 是否正则
    pub case_sensitive: bool,       // 是否区分大小写
    pub include_ignored: bool,      // 是否包含 .gitignore 中的文件
    pub files_to_include: Vec<String>,  // 要包含的文件模式
    pub files_to_exclude: Vec<String>,  // 要排除的文件模式
}

pub struct SearchResult {
    pub path: PathBuf,
    pub matches: Vec<SearchMatch>,
}
```

## 与 AI 的关系

搜索系统直接用于 Agent 工具：
- `GrepTool` — 搜索文件内容（支持正则）
- `FindPathTool` — 按路径搜索文件
- `DiagnosticsTool` — 搜索诊断信息

这些工具是 AI Agent 理解代码库的核心能力。

## 与反向代理的关系

不相关，搜索系统是纯本地实现。

## 关键文件

- `crates/search/src/search.rs` — 搜索实现
- `crates/project/src/project_search.rs` — 项目搜索 API