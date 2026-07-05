# 循环分析报告 #23 — Google AI / Gemini Provider

**分析时间**: 2026-07-06
**源码位置**: `crates/google_ai/src/` (1,597 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 原生支持 Google AI（Gemini）API，使用 API Key 直连。

## API 端点

```
https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={api_key}
```

认证方式：API Key 作为 URL 查询参数 `key=`，非 Bearer Token。

## 流式响应

使用 SSE (Server-Sent Events) 格式，每行以 `data: ` 前缀开头。

## 请求体

Gemini 使用 Google 的原生 `GenerateContentRequest` 格式，包含：
- `contents` — 对话内容（`Content` 数组，每个有 `role: user/model`）
- `system_instruction` — 系统指令
- `tools` — 工具定义（FunctionCall, FunctionResponse）

## 与反向代理的关系

Google AI 直连模式不经过 cloud.zed.dev。用户自备 API Key 即可使用。

## 关键文件

- `crates/google_ai/src/google_ai.rs` — API 接口、请求体序列化
- `crates/google_ai/src/completion.rs` — 事件映射（Google → Zed 内部格式）