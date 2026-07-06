# 循环分析报告 #47 — Agent 技能工具 (SkillTool)

**分析时间**: 2026-07-06
**源码位置**: `crates/agent/src/tools/skill_tool.rs` (815 行)
**分析前状态**: ❌ 完全没碰过

## 概述

`SkillTool` 是 Agent 的技能/提示词工具，允许 Agent 在对话中动态加载预定义的技能提示词。

## 核心功能

```rust
pub struct SkillToolInput {
    pub name: String,  // 要加载的技能名称
}

pub enum SkillToolOutput {
    Found { rendered: String },  // 技能内容已渲染
    NotFound { name: String },   // 技能未找到
}
```

## 技能渲染

`render_skill_envelope()` 函数将技能内容包装为 `<skill_content>` XML 标签格式，确保模型驱动的技能激活和 `/` 命令激活在对话中看不出区别。

## 与反向代理的关系

技能系统是本地功能，Agent 工具不涉及网络调用。不影响反向代理方案。

## 关键文件

- `crates/agent/src/tools/skill_tool.rs` — 技能工具实现