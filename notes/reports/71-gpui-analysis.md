# 分析报告 — GPUI (Zed 的 GUI 框架)

**源码位置**: `crates/gpui/src/` (33,097 行)
**分析前状态**: ❌ 完全没碰过

## 概述

GPUI 是 Zed 的自研 GUI 框架，用 Rust 实现，支持多平台（macOS、Linux、Windows、Web）。

## 核心模块

| 模块 | 行数 | 说明 |
|------|------|------|
| `window.rs` | 6,265 | 窗口管理、事件循环 |
| `geometry.rs` | 3,996 | 几何计算（点、尺寸、矩形、变换） |
| `app.rs` | 2,822 | 应用生命周期、全局状态 |
| `platform.rs` | 2,518 | 平台抽象层 |
| `element.rs` | — | UI 元素 |
| `scene.rs` | — | 场景渲染 |

## 核心特性

- **响应式**：基于 `Entity` + `Subscription` 的响应式模型
- **GPU 加速**：通过 `wgpu` 实现跨平台 GPU 渲染
- **多平台**：macOS (Metal)、Linux (Vulkan/OpenGL)、Web (WebGL)
- **自定义布局**：Flexbox 风格布局
- **字体渲染**：使用 `cosmic-text` 或 `swash` 进行文本布局

## 与 AI 的关系

GPUI 不直接参与 AI 通信协议，但 Agent UI（聊天面板、工具调用渲染）全部基于 GPUI。

## 关键文件

- `crates/gpui/src/window.rs` — 窗口系统
- `crates/gpui/src/app.rs` — 应用核心
- `crates/gpui/src/geometry.rs` — 几何计算