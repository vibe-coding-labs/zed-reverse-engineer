# 循环分析报告 #16 — 提示词存储 (Prompt Store)

**分析时间**: 2026-07-06
**源码位置**: `crates/prompt_store/src/` (1,967 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Prompt Store 是 Zed 的本地提示词存储系统，使用 LMDB (heed) 嵌入式数据库持久化用户自定义的提示词。它管理的是**提交信息 prompt**等用户可自定义的模板，不是 AI Agent 的 system prompt。

## 存储结构

- **数据库**: LMDB (Lightning Memory-Mapped Database)
- **最大容量**: 1GB
- **表**: `metadata.v2` + `bodies.v2`
- **位置**: `~/.local/share/zed/prompts/prompts-library-db.0.mdb`

## 内置提示词

目前只有一个内置提示词 `BuiltInPrompt::CommitMessage`，用于生成 Git 提交信息。

## 自定义提示词

用户可以通过 Zed 界面创建自定义提示词，存储在本地 LMDB 数据库中。

## 与反向代理的关系

不相关。Prompt Store 是本地存储，不涉及网络通信。

## 关键文件

- `crates/prompt_store/src/prompt_store.rs` — 核心存储实现
- `crates/prompt_store/src/prompts.rs` — 提示词类型定义
- `crates/prompt_store/src/rules_to_skills_migration.rs` — 规则→技能迁移
- `crates/git_ui/src/commit_message_prompt.txt` — 内置的 commit message prompt 模板