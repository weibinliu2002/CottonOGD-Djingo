/// <reference types="vite/client" />

// 旧版 CommonJS 包（BioJS msa / MSAViewer），无类型声明，按需动态导入
declare module 'msa'
// underscore 作为 msa 的全局 `_` 注入，按需动态导入（亦无类型声明）
declare module 'underscore'
