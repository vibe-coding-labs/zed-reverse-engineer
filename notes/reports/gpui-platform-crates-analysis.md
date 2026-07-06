# 分析报告 — GPUI 平台后端 crate 批量

| crate | 行数 | 用途 | AI 相关？ |
|-------|------|------|----------|
| `gpui_linux` | 13,590 | Linux 平台后端 (X11/Wayland/Vulkan) | ❌ |
| `gpui_windows` | 11,331 | Windows 平台后端 (DirectX) | ❌ |
| `gpui_macos` | 11,566 | macOS 平台后端 (Metal) | ❌ |
| `gpui_wgpu` | 3,995 | wgpu 跨平台 GPU 抽象 | ❌ |
| `gpui_macros` | 3,222 | GPUI derive 宏 | ❌ |
| `gpui_web` | 2,537 | Web 平台后端 (WebGL) | ❌ |
| `gpui_util` | 589 | GPUI 工具函数 | ❌ |
| `gpui_platform` | 186 | 平台 trait 定义 | ❌ |
| `gpui_tokio` | 100 | Tokio executor 集成 | ❌ |
| `gpui_shared_string` | — | 共享字符串优化 | ❌ |

所有 GPUI 平台 crate 不包含 AI 或网络协议逻辑。