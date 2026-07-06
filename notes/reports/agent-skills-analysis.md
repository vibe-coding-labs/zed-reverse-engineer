# 分析报告 — Agent 技能系统 (agent_skills)

**源码位置**: `crates/agent_skills/agent_skills.rs` (2,187 行)
**分析前状态**: ❌ 完全没碰过

## 概述

Agent 技能系统管理所有 Agent 可用的技能（Skill），每个技能是一个包含 `SKILL.md` 的目录。

## 目录结构

```
~/.agents/skills/          # 全局技能目录
  ├── my-skill/
  │   ├── SKILL.md         # 技能定义文件（最多 100KB）
  │   └── ...              # 技能资源文件
  └── another-skill/
      └── SKILL.md

.zed/.agents/skills/       # 项目级技能目录（覆盖全局）
```

## 技能定义

```rust
pub struct Skill {
    pub name: String,                    // 技能名称
    pub description: String,             // 描述（最多 50KB）
    pub source: SkillSource,             // 来源
    pub directory_path: PathBuf,         // 技能目录路径
    pub skill_file_path: PathBuf,        // SKILL.md 路径
    pub disable_model_invocation: bool,  // 是否禁用模型主动调用
    pub embedded_body: Option<&'static str>, // 内置技能内容
}

pub enum SkillSource {
    BuiltIn,          // 编译到二进制中
    Global,           // ~/.agents/skills/
    Project,          // .zed/.agents/skills/
}
```

## 限制

- 单个 SKILL.md 最大 100KB
- 所有技能描述总大小最大 50KB（防止 system prompt 过长）
- 并发 I/O 限 16 路（防止大量技能耗尽文件描述符）

## 技能加载优先级

1. **BuiltIn**（最低）→ **Global** → **Project**（最高，同名覆盖）

## 关键文件

- `crates/agent_skills/agent_skills.rs` — 技能加载和管理