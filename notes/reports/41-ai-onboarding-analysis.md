# 循环分析报告 #41 — AI Onboarding (AI 入门引导)

**分析时间**: 2026-07-06
**源码位置**: `crates/ai_onboarding/src/` 
**分析前状态**: ❌ 完全没碰过

## 概述

AI Onboarding crate 管理 Zed 的 AI 功能入门引导流程，包括签订服务条款、开始 Pro 试用等。

## 核心流程

```rust
pub struct AiOnboarding {
    pub accepted_terms_at: Option<Timestamp>,
    pub account_too_young: bool,
    // 引导步骤状态
}
```

## 引导步骤

1. **签署服务条款** — 首次使用 AI 功能时要求用户同意 Zed 的服务条款
2. **开始试用** — 展示 14 天免费试用的信息
3. **配置 Provider** — 引导用户配置 AI Provider（自带 Key 或登录 Zed）

## 关键约束

- `account_too_young: true` 时 GitHub 账号小于 30 天，不能开始试用
- `YoungAccountBanner` 组件显示禁止试用的提示信息
- `eligible_for_trial = trial_started_at.is_none()` 每个账号只可试用一次

## 关键文件

- `crates/ai_onboarding/src/ai_onboarding.rs` — 引导流程核心
- `crates/ai_onboarding/src/young_account_banner.rs` — 账号年龄限制提示