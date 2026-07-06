# 循环分析报告 #63 — Markdown 处理

**分析时间**: 2026-07-06
**源码位置**: `crates/markdown/src/` (7,685 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`markdown` crate 提供完整的 Markdown 解析、渲染和 HTML 导出功能，用于 Agent 对话中的消息渲染。

## 核心模块

| 模块 | 行数 | 说明 |
|------|------|------|
| `markdown.rs` | 4,840 | Markdown 渲染引擎 |
| `parser.rs` | 1,667 | Markdown 解析器 |
| `mermaid.rs` | 930 | Mermaid 图表渲染 |
| `path_range.rs` | 245 | 路径范围标记 |
| `html.rs` | — | HTML 导出 |

## 渲染能力

- 代码块高亮（支持语言检测）
- Mermaid 图表渲染
- 内联格式（粗体、斜体、代码）
- 链接、图片
- 表格
- 任务列表

## Agent 使用

Agent 的 AI 响应以 Markdown 格式返回，由该 crate 渲染为富文本显示在对话界面中。

## 关键文件

- `crates/markdown/src/markdown.rs` — 渲染引擎
- `crates/markdown/src/parser.rs` — 解析器
- `crates/markdown/src/mermaid.rs` — Mermaid 支持