# 循环分析报告 #22 — Language 系统核心

**分析时间**: 2026-07-06
**源码位置**: `crates/language/src/language.rs` (1,993 行) + 整个 `language` crate 22,523 行
**分析前状态**: ❌ 完全没碰过

## 概述

`language` crate 是 Zed 语言支持的核心，基于 Tree-sitter 提供语法解析、高亮、符号大纲等功能。

## 核心类型

```rust
pub struct Language {
    // 语言配置（括号、注释、格式化等）
    config: LanguageConfig,
    // Tree-sitter 语法
    grammar: Option<Grammar>,
    // LSP 适配器缓存
    cached_lsp_adapter: CachedLspAdapter,
}

pub struct LanguageScope {
    // 语言作用域——支持内嵌语言（HTML 中的 JS 等）
}
```

## 语言设置

`language_settings` 模块中包含与 AI 相关的设置：
- `EditPredictionPromptFormat` — 编辑预测 prompt 格式
- `EditPredictionsMode` — 编辑预测模式
- `ZetaVersion` — Zeta2 模型版本

## 与反向代理的关系

Language 系统负责解析代码、提供符号信息给 Agent。这些是 Agent 工具（GrepTool、ReadFileTool 等）的基础，但不涉及网络协议。不影响反向代理方案。

## 关键文件

- `crates/language/src/language.rs` — Language 核心类型
- `crates/language/src/language_settings.rs` — 语言相关设置（含编辑预测配置）
- `crates/language/src/buffer.rs` — 缓冲区实现