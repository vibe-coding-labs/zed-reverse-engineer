# 循环分析报告 #44 — Agent 编辑文件工具 (EditFileTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/edit_file_tool.rs` (2,960 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`EditFileTool` 是 AI Agent 最核心的工具之一，负责编辑项目中的文件。

## 输入参数

```rust
pub struct EditFileToolInput {
    /// 文件路径（相对于项目根目录）
    pub path: PathBuf,
    /// 编辑操作列表（按顺序应用）
    pub edits: Vec<Edit>,
}
```

每个 Edit 包含 `old_text` 和 `new_text`，实现**查找-替换**操作。

## 流式编辑

`EditFileTool` 支持流式输入（`EditFileToolPartialInput`），允许 LLM 在生成完整响应前就开始应用编辑。

## 文件操作跟踪

- 每次编辑前备份缓冲区状态
- 支持撤销（Undo）
- 冲突检测——如果文件内容被外部修改，Agent 会检测到冲突并报告

## 关键文件

- `crates/agent/src/tools/edit_file_tool.rs` — 编辑工具实现
- `crates/agent/src/tools/write_file_tool.rs` — 写入文件工具 (1,465 行)
- `crates/agent/src/tools/read_file_tool.rs` — 读取文件工具 (2,043 行)