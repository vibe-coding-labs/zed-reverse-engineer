# 分析报告 — settings_content 配置内容结构

**源码位置**: `crates/settings_content/src/settings_content.rs`

## 概述

`SettingsContent` 是 Zed 用户配置的根结构体，定义了 `settings.json` 中的所有顶层字段。

## 核心结构

```rust
pub struct SettingsContent {
    pub calls: Option<CallSettingsContent>,
    pub telemetry: Option<InstrumentationSettingsContent>,
    pub features: Option<FeatureFlagsMap>,
    pub performance_profile: Option<PerformanceProfilerSettingsContent>,
    pub audio: Option<AudioSettingsContent>,
    pub debugger: Option<DebuggerSettingsContent>,
    pub extensions: Option<ExtensionsSettingsContent>,
    pub language_models: Option<AllLanguageModelSettingsContent>,
    pub server_url: Option<String>,
    pub credentials_url: Option<String>,
}
```

## 关键字段

| 字段 | 说明 |
|------|------|
| `server_url` | 覆盖 Zed 服务器地址（默认 `https://zed.dev`） |
| `credentials_url` | 凭证存储 URL（默认同 server_url） |
| `language_models` | LLM Provider 配置（API Key、端点等） |
| `telemetry` | 遥测配置（metrics_enabled、diagnostics_enabled） |
| `extensions` | 扩展管理设置 |
| `features` | 功能开关 |

## 覆盖优先级

1. 环境变量 (`ZED_SERVER_URL`) → 最高优先级
2. 用户 `settings.json` (`server_url` 字段)
3. 默认值 (`https://zed.dev`)

## 与反向代理的关系

`server_url` 是反向代理方案的核心控制点。设置 `ZED_SERVER_URL=http://localhost:3000` 可以劫持所有 Zed Cloud API 流量。