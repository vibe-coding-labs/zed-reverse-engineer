# 循环分析报告 #14 — Web Search (AI 网络搜索集成)

**分析时间**: 2026-07-05
**源码位置**: `crates/web_search/` + `crates/web_search_providers/` (237 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed AI Agent 支持网络搜索功能，作为 Agent 工具提供给 LLM 调用。搜索请求通过 `cloud.zed.dev` 代理。

## API 端点

```
POST /web_search
Authorization: Bearer {llm_token}
Content-Type: application/json
```

## 请求体

```json
{
  "query": "搜索关键词"
}
```

## 响应体

```json
{
  "results": [
    {
      "title": "结果标题",
      "url": "https://example.com",
      "text": "结果摘要文本"
    }
  ]
}
```

## 实现

`CloudWebSearchProvider` 是 Zed 自带的搜索实现（provider_id = `"zed.dev"`），调用 cloud.zed.dev 的 `/web_search` 端点。支持的搜索 Provider 通过 `WebSearchRegistry` 注册，可扩展。

## 与反向代理的关系

Web Search 同样使用 LLM Token 认证，也经过 `cloud.zed.dev`。如果反向代理要完整支持 Zed AI 功能，需要也处理 `/web_search` 端点。

| 端点 | 方法 | 用途 | 是否需代理 |
|------|------|------|-----------|
| `/completions` | POST | AI 对话 | ✅ 核心 |
| `/models` | GET | 模型列表 | ✅ 需要 |
| `/web_search` | POST | 网络搜索 | ⚠️ 可选 |
| `/client/llm_tokens` | POST | Token 获取 | ✅ 需要 |

## 关键文件

- `crates/web_search/src/web_search.rs` — 搜索注册表
- `crates/web_search_providers/src/cloud.rs` — cloud.zed.dev 搜索实现
- `crates/cloud_llm_client/src/cloud_llm_client.rs` — `WebSearchBody`/`WebSearchResponse` 类型定义