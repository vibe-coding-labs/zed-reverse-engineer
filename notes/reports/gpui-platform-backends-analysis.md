# 分析报告 — GPUI macOS 平台后端

**源码位置**: `crates/gpui_macos/src/` (11,566 行)

macOS 平台后端，使用 Metal 渲染。与 AI 协议无关。

## 子模块

| 文件 | 行数 | 功能 |
|------|------|------|
| `window.rs` | 3,147 | 窗口管理（NSWindow） |
| `metal_renderer.rs` | 1,799 | Metal GPU 渲染 |
| `keyboard.rs` | 1,502 | 键盘事件处理 |
| `platform.rs` | 1,438 | 平台抽象实现 |
| `text_system.rs` | 743 | 字体/文本渲染 |
| `display.rs` | 595 | 显示器管理 |
| `pasteboard.rs` | 568 | 剪贴板 |
| `events.rs` | 542 | 事件循环 |
| `metal_atlas.rs` | 403 | GPU 纹理图集 |

## 与 AI 的关系

无。纯平台适配层。

## 其他平台后端

| crate | 行数 | 渲染后端 |
|-------|------|----------|
| `gpui_macos` | 11,566 | Metal |
| `gpui_linux` | 13,590 | Vulkan/EGL |
| `gpui_windows` | 11,331 | DirectX/Vulkan |
| `gpui_web` | ? | WebGL |

所有平台后端均与 AI 协议无关。