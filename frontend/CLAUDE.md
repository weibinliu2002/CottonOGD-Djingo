# CottonOGD Frontend

Vue 3 + Vite + Element Plus 前端（iCotton 棉花组学数据库）。

## 强制要求

- **在此项目中开发或构建前端时，必须先调用 `cottonogd-frontend` skill**（`.claude/skills/cottonogd-frontend/SKILL.md`），遵循其中的 HTTP / i18n / ECharts / 构建验证规范。
- 构建验证只用 `npm run build-only`，不要跑 `npm run build`（type-check 被存量错误阻塞）。
