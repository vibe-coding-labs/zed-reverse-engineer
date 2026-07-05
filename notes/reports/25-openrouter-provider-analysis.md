# 循环分析报告 #25 — OpenRouter Provider

**分析时间**: 2026-07-06
**源码位置**: `crates/open_router/src/` (809 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 支持 OpenRouter 作为 LLM Provider，通过 OpenRouter 的统一 API 访问多种模型。

## API 端点

```
https://openrouter.ai/api/v1/chat/completions
```

认证方式：`Authorization: Bearer {api_key}`
请求头：`X-Title`（可选，用于在 OpenRouter 仪表盘显示）

## 限流处理

OpenRouter 使用 `X-RateLimit-Reset` 响应头通知客户端限流，Zed 会解析该头并等待指定时间后重试。

## 配置

支持通过 `settings.json` 配置：
- `data_collection` — 是否允许 OpenRouter 收集数据
- `model_mode` — 模型调用模式
- 模型选择（可用模型从 OpenRouter API 获取）

## 与反向代理的关系

同其他直连 Provider，不经过 cloud.zed.dev。用户自备 OpenRouter Key。

## 关键文件

- `crates/open_router/src/open_router.rb` — 完整 Provider 实现
- `crates/settings/src/settings.rs` 中 `OpenRouterAvailableModel` — 模型配置