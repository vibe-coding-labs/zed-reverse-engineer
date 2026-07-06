# 循环分析报告 #66 — 编辑器显示映射 (DisplayMap)

**分析时间**: 2026-07-06
**源码位置**: `crates/editor/src/display_map.rs` (4,219 行)
**分析前状态**: ❌ 完全没碰过

## 概述

DisplayMap 是编辑器渲染的核心组件，将缓冲区内容（文本、行号、折叠区域）映射到屏幕坐标系。

## 核心结构

```rust
pub struct DisplayMap {
    pub buffer: Entity<MultiBufferSnapshot>,
    pub scroll_position: Arc<Mutex<ScrollPosition>>,
    pub fold_status: FoldStatus,
    pub highlight: HighlightKey,
}
```

## 关键功能

| 功能 | 说明 |
|------|------|
| 行号映射 | buffer 文本行 → 显示行（含折叠行） |
| 折叠管理 | `FoldStatus` — 代码折叠区域跟踪 |
| 滚动管理 | 滚动位置持久化和恢复 |
| 高亮 | `HighlightKey` — 搜索/诊断高亮 |
| Wrap 支持 | 软换行（通过 `wrap_map` 对齐） |

## 与 AI 的关系

DisplayMap 不直接参与 AI 协议，但 Agent 的编辑操作最终需要在 DisplayMap 上反映出来。

## 关键文件

- `crates/editor/src/display_map.rs` — 显示映射核心
- `crates/editor/src/display_map/` — 子模块（wrap、fold 等）