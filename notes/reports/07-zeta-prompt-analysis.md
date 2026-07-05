# 循环分析报告 #7 — Zeta2 Prompt 构建 (ZetaPrompt)

**分析时间**: 2026-07-05
**源码位置**: `crates/zeta_prompt/src/` (9,805 行)
**分析前状态**: ❌ 完全没碰过

## 概述

ZetaPrompt 是 Zed **自研的 Zeta2 编辑预测模型**的 prompt 构建工具。它负责将代码编辑上下文（光标位置、缓冲区内容、诊断信息、文件结构等）组装成模型可用的 prompt。

## 与 Edit Prediction 的关系

Edit Prediction 使用 Zeta2 模型来预测用户的下一步编辑操作。ZetaPrompt 是这个流程的**数据准备层**。

## 核心数据结构

```rust
pub struct ZetaPromptInput {
    pub buffer: String,                    // 当前缓冲区内容
    pub cursor_offset: usize,              // 光标位置（字节偏移）
    pub cursor_line: u32,                  // 光标行号
    pub cursor_column: u32,                // 光标列号
    pub path: PathBuf,                     // 文件路径
    pub language: String,                  // 语言
    pub tab_size: usize,                   // Tab 大小
    pub line_ending: String,               // 换行符
    pub diagnostics: Vec<ActiveBufferDiagnostic>,  // 诊断信息
    pub related_files: Vec<RelatedFile>,   // 相关文件
    pub recent_edits: Vec<Event>,          // 最近的编辑事件
}
```

## Prompt 格式

Zeta2 支持多种 prompt 格式（`ZetaFormat` 枚举），每种格式有不同的 token 限制和 stop tokens。ZetaPrompt 负责：
1. 计算光标附近的 excerpt range（可编辑区域 + 上下文区域）
2. 组装代码上下文为模型可用的格式
3. 裁剪到模型 token 限制内
4. 添加 special tokens 和 stop tokens

## 编辑事件类型

```rust
pub enum Event {
    Select,       // 选择操作
    Insert,       // 插入文本
    Delete,       // 删除文本
    Replace,      // 替换文本
    NewBuffer,    // 新缓冲区
    Undo,         // 撤销
    Redo,         // 重做
    Cursor,       // 光标移动
    // ... 更多事件类型
}
```

## 与反向代理的关系

Zeta2 编辑预测与 AI 聊天/Agent 是**两套独立的系统**：
- Edit Prediction 使用 Zeta2 模型（Zed 自研），不经过任何外部 API
- AI Chat/Agent 使用外部 LLM（Anthropic/OpenAI），才经过 cloud.zed.dev

所以反向代理方案不需要关心 ZetaPrompt。

## 关键文件

- `crates/zeta_prompt/src/zeta_prompt.rs` — 核心 prompt 构建（6,079 行）
- `crates/zeta_prompt/src/multi_region.rs` — 多区域编辑支持
- `crates/zeta_prompt/src/udiff.rs` — Unified diff 格式支持
- `crates/zeta_prompt/src/excerpt_ranges.rs` — 文字范围计算