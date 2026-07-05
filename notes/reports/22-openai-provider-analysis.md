# 循环分析报告 #22 — OpenAI Provider 实现

**分析时间**: 2026-07-06
**源码位置**: `crates/open_ai/src/` (5,126 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 原生支持 OpenAI API，使用与 Cloud API 平行的直连模式。

## API 端点

```
直连: https://api.openai.com/v1/chat/completions
官方 OpenAI API，用户自备 API Key
```

## 支持的模型

| 模型 | ID | 说明 |
|------|----|------|
| GPT-4 | `gpt-4` | 基础模型 |
| GPT-4o-mini | `gpt-4o-mini` | 快速经济模型 |
| o3 | `o3` | 推理模型 |
| GPT-5 | `gpt-5` | 最新旗舰 |
| GPT-5-mini | `gpt-5-mini` | 默认 |
| GPT-5-nano | `gpt-5-nano` | 轻量 |
| GPT-5.1 | `gpt-5.1` | 迭代版本 |
| GPT-5.2 | `gpt-5.2` | 迭代版本 |
| GPT-5.3-codex | `gpt-5.3-codex` | Codex 代码模型 |

## 实现模块

| 模块 | 行数 | 说明 |
|------|------|------|
| `completion.rs` | 3,274 | Chat Completions API（流式 + 非流式） |
| `open_ai.rs` | 910 | Provider 注册、模型配置 |
| `responses.rs` | 610 | OpenAI Responses API v2 |
| `batches.rs` | 332 | 批量 API 支持 |

## 与反向代理的关系

OpenAI 直连模式不经过 cloud.zed.dev，用户自备 Key 即可使用。影响范围：如果反向代理要让 Zed 能用 OpenAI 模型，不需要劫持任何流量，只要用户配置自己的 API Key 即可。

## 关键文件

- `crates/open_ai/src/completion.rs` — Chat Completions 完整实现
- `crates/open_ai/src/responses.rs` — Responses API v2
- `crates/open_ai/src/open_ai.rs` — Provider 入口