# 循环分析报告 #28 — LM Studio Provider

**分析时间**: 2026-07-06
**源码位置**: `crates/lmstudio/src/` (522 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 支持 LM Studio 本地模型服务，通过 LM Studio 的 HTTP API 调用本地运行的模型。

## API 端点

```
http://localhost:1234/api/v0/chat/completions
```

无认证（本地），使用 OpenAI 兼容格式。

## 流式响应

LM Studio 使用 OpenAI 标准的 SSE 格式，但流式事件通过 JSON Lines（每行一个 JSON）而非标准 SSE 的 `data: ` 前缀传输。

## 模型列表

通过 `GET /api/v0/models` 获取可用模型列表。

## 与反向代理的关系

同 Ollama，本地模型，不影响反向代理方案。

## 关键文件

- `crates/lmstudio/src/lmstudio.rs` — 完整 Provider 实现