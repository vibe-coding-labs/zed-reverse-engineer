# 循环分析报告 #38 — Copilot 核心集成

**分析时间**: 2026-07-06
**源码位置**: `crates/copilot/src/` (3,342 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Copilot 集成是 Zed 的代码补全引擎，支持 GitHub Copilot 和自定义兼容服务器。

## 核心组件

| 模块 | 行数 | 说明 |
|------|------|------|
| `copilot.rs` | 1,901 | Copilot 主引擎（认证、状态、LSP 代理） |
| `copilot_edit_prediction_delegate.rs` | 1,142 | 编辑预测委托（Copilot 作为 Zeta2 替代） |
| `request.rs` | 299 | Copilot 请求构建 |

## 编辑预测委托

Zed 支持将 Copilot 作为编辑预测后端，替代 Zeta2 模型：
- 用户配置 `edit_predictions.mode = "copilot"` 后，Copilot 负责内联代码补全
- `CopilotEditPredictionDelegate` 实现了 Zeta2 的接口

## 认证

Copilot 使用 GitHub OAuth Device Flow 认证（通过 `copilot_ui` crate）。

## 与反向代理的关系

Copilot 是独立功能，不经过 cloud.zed.dev。不影响反向代理方案。

## 关键文件

- `crates/copilot/src/copilot.rs` — 核心引擎
- `crates/copilot/src/copilot_edit_prediction_delegate.rs` — 编辑预测委托