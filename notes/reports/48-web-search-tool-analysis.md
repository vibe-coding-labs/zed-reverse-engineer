# 循环分析报告 #48 — Agent 网络搜索工具 (WebSearchTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/web_search_tool.rs` (166 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`WebSearchTool` 是 Agent 的网络搜索工具，允许 Agent 在对话中搜索互联网获取实时信息。

## 输入参数

```rust
pub struct WebSearchToolInput {
    pub query: String,  // 搜索关键词或问题
}
```

## 执行流程

```
1. Agent 发送 search_web 工具调用
2. 用户授权确认（需用户同意）
3. 通过 WebSearchRegistry 获取活跃的搜索 Provider
4. 调用 provider.search(query) 执行搜索
5. 支持用户取消（cancelled_by_user）
6. 搜索结果格式化后返回给 LLM
```

## Provider 限制

当前仅支持 `ZED_CLOUD_PROVIDER_ID`（`zed.dev`）作为搜索 Provider。搜索请求通过 `cloud.zed.dev` 的 `/web_search` 端点执行。

## 结果格式

搜索结果的标题、URL 和摘要以 `ResourceLink` 格式返回给 LLM。

## 与反向代理的关系

WebSearchTool 使用 cloud.zed.dev 的搜索服务，需要有效的 LLM Token。如果反向代理要完整支持 AI 功能，需要处理 `/web_search` 端点。

## 关键文件

- `crates/agent/src/tools/web_search_tool.rs` — 搜索工具实现
- `crates/web_search_providers/src/cloud.rs` — cloud.zed.dev 搜索实现