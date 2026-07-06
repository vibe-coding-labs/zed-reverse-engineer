# 循环分析报告 #59 — Agent 网页获取工具 (FetchTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/fetch_tool.rs` (180 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`FetchTool` 是 Agent 的 HTTP 请求工具，允许 LLM 获取网页内容并转换为 Markdown。

## 输入参数

```rust
pub struct FetchToolInput {
    pub url: String,  // 要获取的 URL
}
```

## 内容处理

| Content-Type | 处理方式 |
|-------------|---------|
| text/html | 转换为 Markdown（支持 Wikipedia 特殊处理） |
| text/plain | 直接返回纯文本 |
| application/json | 格式化 JSON 并返回 |

## HTML 转换支持

- **通用**: 段落、标题、列表、表格、样式文本
- **Wikipedia 特殊**: 去除导航元素、处理信息框、代码块

## 自动补全 URL

如果 URL 不以 `http://` 或 `https://` 开头，会自动添加 `https://` 前缀。

## 关键文件

- `crates/agent/src/tools/fetch_tool.rs` — 获取工具实现