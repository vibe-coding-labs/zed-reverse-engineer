# 循环分析报告 #54 — Agent 读取文件工具 (ReadFileTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/read_file_tool.rs` (2,043 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`ReadFileTool` 是 Agent 的读文件工具，支持读取项目中的指定文件内容。

## 输入参数

```rust
pub struct ReadFileToolInput {
    pub path: String,              // 文件路径（相对于项目根目录）
    pub start_line: Option<u32>,   // 起始行号（1-based）
    pub end_line: Option<u32>,     // 结束行号（1-based，包含）
}
```

## 主要特性

- **路径安全**：拒绝以 `.` 或 `..` 开头的路径（防止目录遍历攻击）
- **全局技能路径**：支持读取 `~/.agents/skills/` 下的技能文件
- **可滚动**：支持分页读取（防止一次性加载过多 token）
- **已删除文件**输出清晰错误提示
- **代码块渲染**：读取的内容以 Markdown 代码块格式返回给 LLM

## 关键文件

- `crates/agent/src/tools/read_file_tool.rs` — 读文件工具实现