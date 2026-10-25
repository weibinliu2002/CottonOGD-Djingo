---
name: cottonogd-frontend
description: CottonOGD/iCotton 棉花组学数据库前端（Vue 3 + Vite + Element Plus）的开发与构建规范。在本项目中创建/修改组件、页面、store、样式，或执行前端构建验证时使用。
---

# CottonOGD 前端开发规范

以下约定均来自项目现状验证（2026-10），执行前端任务前先读一遍。

## 技术栈与结构

- Vue 3.5 组合式 API（`<script setup lang="ts">`）+ Vite 7 + Element Plus 2.13 + Pinia + vue-router 4 + vue-i18n（legacy: false）
- 目录：页面 `src/views/<域>/`，复用组件 `src/components/<域>/`，store `src/stores/modules/*.ts`，组合式函数 `src/composables/`
- 路径别名 `@` → `src/`；新组件用 PascalCase 命名，参考 `src/components/home/ChatWidget.vue`

## 自动导入（容易踩坑）

- Element Plus 组件（el-button、el-card…）和 `ElMessage` 由 unplugin 自动导入，**不要手写 import**
- Element Plus 图标**必须显式 import**：`import { Search, Loading } from '@element-plus/icons-vue'`
- el-button 的 size 只接受 `'' | 'default' | 'small' | 'large'`，写 `medium` 会告警（存量代码有此问题，新代码不要复制）

## HTTP 调用

- **新代码统一用 `@/utils/api`**（`apiGet/apiPost/apiPut/apiDelete`，泛型直接返回业务数据），不要直接 import `http.js` 后 `as any`
- 认证、401 自动重登重放、CSRF 头、错误处理全部由 `http.js` 拦截器完成，组件里不要重复实现
- 后端契约：所有业务接口走 `/CottonOGD_api/*`（vite 代理到 `DJANGO_TARGET`，生产走 Nginx 同源反代）；响应里的字符串 JSON 字段（如 `geneid_result`）需要手动 `JSON.parse`
- AI 对话：`POST /CottonOGD_api/ai/chat/`，请求 `{message, clear_history?}`，响应 `{success, answer, tool_calls, history_turns}`，历史在服务端 Redis；LLM 较慢，前端超时给 120s
- 后端接口不一定都存在：对接前先用 `curl --noproxy '*' http://localhost:5713/CottonOGD_api/xxx/` 验证，失败时前端静默回退（参考 NewsBox）

## i18n（双语必须同步）

- 所有用户可见文案放 `src/locales/i18n/en-US.json` 和 `zh-CN.json`，**两个文件必须同时加同一个键**，否则运行时告警
- 文案用 `t('key')`，键名全小写下划线；存量有缺键告警（transposons 等），新代码不要新增缺口

## ECharts（按需引入）

- 一律 `import echarts from '@/utils/echarts'`（按需注册模块），**禁止** `import * as echarts from 'echarts'`（全量 1.1MB）
- 需要新图表类型/组件时，在 `src/utils/echarts.ts` 的 `echarts.use([...])` 里补注册，不要绕过
- 实例要在 `onBeforeUnmount` dispose，`window.resize` 监听要成对移除

## 样式

- scoped style；主色 `#3a6ea5`（hover 深色 `#2c5282`），辅助渐变 `linear-gradient(135deg, #3a6ea5, #7297bd)`，浅色背景用 `#f8f9fa` 区块 + 白卡片 + `#e9ecef` 边框、12px 圆角
- 断点 768px；固定定位元素注意避开右下角 `el-backtop`（bottom: 40px）

## 构建与验证（重要）

- **用 `npm run build-only` 验证构建，不要跑 `npm run build`**：`type-check`（vue-tsc）被 `src/views/test/tree.vue` 的存量 TS 错误阻塞（历史遗留，未修复前绕过）
- dev server：`npm run dev`，端口 5713；改了 `vite.config.js` 必须重启才生效
- 代理目标从 `.env.local` 读（`DJANGO_TARGET` / `BLAST_TARGET`，默认内网 `172.28.226.114`）；`.env.local` 不进 git
- 完整验证流程：`npm run build-only` 通过 → 起 dev server → 浏览器打开页面确认渲染（canvas 图表不进无障碍快照，需截图确认）→ 控制台无新增错误
- 本机 7897 系统代理访问不了内网 IP，curl 测后端必须加 `--noproxy '*'`（浏览器走 vite 同源代理不受影响）

## 存量债务（改到相关文件时顺手处理，不主动大改）

- `src/views/test/tree.vue` TS 错误阻塞 type-check（见上）
- `http.js` 为 JS，老调用处直接用实例；新代码走 `api.ts` 即可
- `dist/` 被纳入 git 跟踪，构建后会出现大量 D/M 状态，提交时注意区分
