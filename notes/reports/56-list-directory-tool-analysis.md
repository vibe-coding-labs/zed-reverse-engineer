# 循环分析报告 #56 — Agent 列出目录工具 (ListDirectoryTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/list_directory_tool.rs` (1,253 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`ListDirectoryTool` 是 Agent 的目录列表工具，允许 LLM 浏览项目目录结构。

## 输入参数

```rust
pub struct ListDirectoryToolInput {
    pub path: String,  // 目录路径（相对于项目根目录）
}
```

## 主要特性

- **目录树**：返回目录下的文件和子目录列表
- **最大深度**：限制递归深度避免过 deep 的目录树浪费 token
- **全局技能目录**：支持读取 `~/.agents/skills/` 下的技能目录
- **缓存**：结果缓存减少文件系统访问

## 目录结构格式

返回结果以树形结构展示，每个文件和子目录一行，用缩进表示层级关系。

## 关键文件

- `crates/agent/src/tools/list_directory_tool.rs` — 目录列表工具实现