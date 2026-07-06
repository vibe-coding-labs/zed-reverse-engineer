# 分析报告 — Edit Prediction (编辑预测) crate 批量

| crate | 行数 | 用途 | AI 相关？ |
|-------|------|------|----------|
| `edit_prediction_cli` | 18,020 | Edit Prediction CLI 评估工具 | ✅ 编辑预测评估 |
| `edit_prediction` | 14,731 | 核心编辑预测引擎 | ✅ Zeta2 预测引擎 |
| `edit_prediction_metrics` | 6,929 | 编辑预测指标收集 | ✅ 指标 |
| `edit_prediction_context` | 4,166 | 编辑预测上下文构建 | ✅ 上下文 |
| `edit_prediction_ui` | 3,682 | 编辑预测 UI | ✅ UI |
| `edit_prediction_types` | 396 | 编辑预测类型定义（已分析） | ✅ 类型 |

Edit Prediction 全链路已分析：ZetaPrompt（prompt 构建）→ edit_prediction（预测引擎）→ edit_prediction_types（协议格式/反馈）。这些 crate 使用 Zed Cloud 的 `/edit_predictions` API 端点，使用相同的 LLM Token 认证机制。