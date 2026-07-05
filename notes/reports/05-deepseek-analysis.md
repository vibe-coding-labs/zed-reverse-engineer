# 循环分析报告 #5 — DeepSeek 集成

**分析时间**: 2026-07-04
**源码位置**: `crates/deepseek/src/deepseek.rs` (341 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 支持 DeepSeek 作为 LLM Provider，直接连接到 `api.deepseek.com/v1`。

## 协议细节

**端点**: `https://api.deepseek.com/v1/chat/completions`
**认证**: `Authorization: Bearer {api_key}`

使用 OpenAI 兼容的 Chat Completions 格式。

## 支持的模型

| 模型 | ID | 说明 |
|------|----|------|
| DeepSeek V4 Flash | `deepseek-v4-flash` | 快速模型 |
| DeepSeek V4 Pro | `deepseek-v4-pro` | 默认模型 |
| 自定义 | `custom` | 用户自定义模型名 |

## 流式响应

使用 OpenAI 标准的 SSE 格式，每行 `data: {...}`。

## 与反向代理的关系

DeepSeek 直连模式不经过 Zed Cloud，跟自带 API Key 逻辑一样，不影响反向代理方案。

## 关键文件

- `crates/deepseek/src/deepseek.rs` — 完整实现（341 行，小巧但完整）