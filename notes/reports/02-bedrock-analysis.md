# 循环分析报告 #2 — Amazon Bedrock 集成

**分析时间**: 2026-07-04
**源码位置**: `crates/bedrock/src/` (1,339 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 通过 Amazon Bedrock 服务调用 Claude 模型，这是 AWS 托管的 Anthropic 模型服务。用户使用 AWS 凭证（AK/SK 或 IAM Role）认证。

## 协议细节

### 认证方式

与直连 Anthropic API 不同，Bedrock 使用 **AWS Signature V4** 签名：

```
// 不需要 API Key
// 需要: AWS_ACCESS_KEY_ID + AWS_SECRET_ACCESS_KEY + AWS_REGION
// 或者: IAM Role (EC2/ECS/Lambda 自动获取)
```

### 请求端点

```
https://bedrock-runtime.{region}.amazonaws.com/model/{model_id}/invoke-with-response-stream
```

### 支持的模型

| 模型 | ID |
|------|----|
| Claude Sonnet 4 | `anthropic.claude-sonnet-4-20250514-v1:0` |
| Claude Opus 4.8 | `anthropic.claude-opus-4-8-v1:0` |
| Claude Haiku 3.5 | `anthropic.claude-3-5-haiku-20241022-v1:0` |

### 流式响应

Bedrock 返回的是 AWS 标准的 `ResponseStream`，Zed 需要将 Bedrock 的 `Chunk` 格式转换为内部的 `LanguageModelCompletionEvent`。

## 与反向代理的关系

Bedrock 集成方式跟 Cloud API 完全不同：
- 不经过 cloud.zed.dev
- 直连 AWS 区域端点
- 使用 AWS SigV4 而非 Bearer Token

这意味着反向代理只需要处理 Cloud API 的 `/completions` 即可，Bedrock 集成不需要劫持。

## 关键文件

- `crates/bedrock/src/bedrock.rs` — Provider 实现，模型列表
- `crates/bedrock/src/models.rs` — 模型配置（含 `max_token_count`、`supports_tools` 等）