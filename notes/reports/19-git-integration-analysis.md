# 循环分析报告 #19 — Git 集成 (核心实现)

**分析时间**: 2026-07-06
**源码位置**: `crates/git/src/` (7,669 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Zed 的 Git 集成是原生实现（不依赖外部 git 命令行），直接在 Rust 中解析 `.git` 目录结构。

## 核心功能

| 模块 | 文件 | 行数 | 说明 |
|------|------|------|------|
| Repository | `repository.rs` | 5,317 | 完整 Git 仓库操作（暂存、提交、分支、远程） |
| Status | `status.rs` | 775 | 文件状态检测 |
| Blame | `blame.rs` | 447 | 代码溯源 |
| Commit | `commit.rs` | — | 提交操作 |

## 关键发现

- Zed 使用原生 Git 实现，不依赖 `git` 命令行
- 支持 `COMMIT_EDITMSG` 提交信息、`index.lock` 冲突检测
- `.gitignore` 和 `.gitattributes` 支持
- 提交信息通过 `prompt_store` 集成 AI 生成功能

## 与 AI/反向代理的关系

Git 操作中跟 AI 相关的点：
- **AI 生成提交信息**: 通过 `prompt_store::BuiltInPrompt::CommitMessage` 调用 LLM 生成 commit message
- **Agent 的 Git 工具**: Agent 可以执行 git 操作（branch、commit、diff 等）

## 关键文件

- `crates/git/src/repository.rs` — 完整 Git 仓库操作
- `crates/git/src/status.rs` — 文件变更状态
- `crates/git/src/git.rs` — Git 路径常量和基础类型