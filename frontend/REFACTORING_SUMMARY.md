# 前端代码重构总结

## 重构概述

本次重构对 CottonOGD 前端项目进行了全面的代码组织和架构优化，按业务模块重新分类整理了所有源代码文件。

## 主要改进

### 1. 目录结构重组

#### Views（视图组件）
按功能模块重新组织：
- **common/** - 通用页面（Home, About, Contact, Download）
- **genome/** - 基因组浏览（BrowseGenome, Jbrowse, IGV, Synteny, GeneLocation）
- **annotation/** - 注释分析（GO/KEGG Annotation）
- **enrichment/** - 富集分析（GO/KEGG Enrichment）
- **expression/** - 表达分析（Gene Expression）
- **sequence/** - 序列分析（BLAST, ID Search, Region Search）
- **visualization/** - 可视化工具（Circos, Phylotree, PPI, Heatmap）
- **tools/** - 其他工具（TF, TR, Primer Design）

#### Stores（状态管理）
统一移至 `stores/modules/`：
- genome.ts - 基因组相关状态
- geneSearch.ts - 基因搜索状态
- annotation.ts - 注释相关状态
- enrichment.ts - 富集分析状态
- expression.ts - 表达分析状态
- blast.ts - BLAST 相关状态
- family.ts - 基因家族状态
- navigation.ts - 导航状态
- primer.ts - 引物设计状态
- uuid.ts - UUID 生成状态

#### Composables（组合式函数）
按用途分类：
- **features/** - 业务功能相关（useGenomeBrowser, useSequenceCache, useLengthSelector）
- **core/** - 核心通用功能（useAsyncTask, useModal）

#### Components（可复用组件）
按类型分类：
- **layout/** - 布局组件（LanguageSelector）
- **data-display/** - 数据展示组件（GeneInfoCard, SequenceDisplay, TranscriptSelector）

### 2. 路由优化

#### 新路由结构
采用更语义化的路径：
- `/genome/*` - 基因组浏览器相关
- `/sequence/*` - 序列分析工具
- `/annotation/*` - 功能注释
- `/enrichment/*` - 富集分析
- `/expression/*` - 表达分析
- `/visualization/*` - 可视化工具

#### 向后兼容
保留了旧路由路径作为重定向，确保外部链接和书签仍然有效：
```javascript
{ path: '/tools/id-search', redirect: '/sequence/search' }
{ path: '/jbrowse', redirect: '/genome/jbrowse' }
// ... 等等
```

### 3. 导入路径更新

所有文件的导入路径已更新为新的目录结构：
```typescript
// Before
import { useBlastStore } from '@/stores/blastStore'
import HomeView from '@/views/HomeView.vue'

// After
import { useBlastStore } from '@/stores/modules/blast'
import HomeView from '@/views/common/HomeView.vue'
```

## 技术细节

### 使用的技术栈
- Vue 3.5.27 + TypeScript ~5.9.3
- Element Plus 2.13.2
- Pinia 3.0.4 (状态管理)
- Vue Router 4.6.4 (路由)
- Vite 7.3.0 (构建工具)

### 模块化优势
1. **更好的可维护性** - 相关功能代码集中在一起
2. **清晰的职责划分** - 每个模块负责特定的业务领域
3. **便于团队协作** - 减少文件冲突
4. **易于扩展** - 新功能可以直接添加到对应模块

## 注意事项

### 待修复的类型错误
TypeScript 检查发现一些类型问题需要后续修复：
- 部分组件缺少明确的类型定义
- 某些 store 方法的参数需要添加类型注解
- 一些可选属性的空值处理需要完善

### 兼容性说明
- 所有旧路由都配置了重定向，保证向后兼容
- 建议逐步更新代码中的路由引用到新路径
- 外部 API 调用不受影响

## 下一步计划

1. **UI/UX 优化**
   - 更新 App.vue 头部和导航栏设计
   - 优化首页视觉效果
   - 创建全局样式系统

2. **代码质量提升**
   - 修复 TypeScript 类型错误
   - 统一错误处理机制
   - 添加单元测试

3. **性能优化**
   - 实现路由懒加载
   - 优化大组件的代码分割
   - 缓存策略优化

## 验证步骤

运行以下命令验证重构结果：

```bash
# 安装依赖（如果需要）
npm install

# 类型检查
npm run type-check

# 开发服务器
npm run dev

# 生产构建
npm run build
```

---

重构完成时间：2026-06-14
重构范围：全部前端源代码（src/）
