# 循环分析报告 #27 — Ollama 本地模型 Provider

**分析时间**: 2026-07-06
**源码位置**: `crates/ollama/src/` (825 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 支持 Ollama 本地模型，通过 Ollama 运行本地开源模型。

## API 端点

```
http://localhost:11434/api/chat
```

无认证（本地），Ollama API 兼容 OpenAI 的 Chat Completions 格式。

## 配置

```json
{
  "language_models": {
    "ollama": {
      "api_url": "http://localhost:11434",
      "keep_alive": "5m"
    }
  }
}
```

- `api_url` — 可自定义 Ollama 服务器地址
- `keep_alive` — 模型保持加载时间（默认 `5m`）
- `model` — 模型名称（从 Ollama API 自动获取列表）

## 模型能力

Ollama 模型能力由模型元数据决定（`Model` 结构体），包含 `max_tokens`、`supports_tools`、`supports_images` 等字段，通过 `GET /api/tags` 获取。

## 流式响应

使用 OpenAI 兼容的 SSE 格式流式返回。

## 与反向代理的关系

Ollama 是本地模型，完全不需要网络代理。不影响反向代理方案。

## 关键文件

- `crates/ollama/src/ollama.rs` — 完整 Provider 实现（825 行）