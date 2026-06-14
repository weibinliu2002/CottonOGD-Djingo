# 图片使用与更换指南

## 快速开始

### 1. 添加新图片

将您的图片文件放到 `src/assets/images/` 目录下：

```
src/assets/images/
├── logo.svg              # Logo（已有）
├── favicon.png           # 网站图标（已有）
├── mh.png                # 示意图（已有）
├── egg.jpg               # 棉花图片（已有）
├── screenshot-dashboard.png  # 仪表盘截图（已有）
├── screenshot-search.png     # 搜索截图（已有）
└── your-new-image.jpg    # 您的新图片
```

### 2. 在配置中注册

编辑 `src/config/theme.config.ts`：

```typescript
export const images = {
  // 添加您的图片配置
  myNewImage: '@/assets/images/your-new-image.jpg',
} as const
```

### 3. 在组件中使用

#### 方法一：通过配置文件（推荐）

```vue
<script setup>
import { images } from '@/config/theme.config'
</script>

<template>
  <img :src="images.myNewImage" alt="描述">
</template>
```

#### 方法二：直接导入

```vue
<template>
  <img src="@/assets/images/your-new-image.jpg" alt="描述">
</template>
```

#### 方法三：动态加载

```vue
<script setup>
import { ref } from 'vue'

const imageUrl = ref('@/assets/images/your-new-image.jpg')
</script>

<template>
  <img :src="imageUrl" alt="描述">
</template>
```

## 更换现有图片

### 示例：更换首页背景图

**当前配置** (`theme.config.ts`):
```typescript
heroBackground: '@/assets/images/mh.png',
```

**更换步骤**:

1. 准备新图片，例如 `new-hero.jpg`
2. 放到 `src/assets/images/` 目录
3. 修改配置：
   ```typescript
   heroBackground: '@/assets/images/new-hero.jpg',
   ```
4. 保存即可全局生效

## 图片优化建议

### 格式选择
- **PNG**: Logo、图标、需要透明度的图片
- **JPG/JPEG**: 照片、复杂渐变的图片
- **SVG**: 矢量图形、Logo（可无限放大不失真）
- **WebP**: 现代格式，文件大小更小（推荐使用）

### 尺寸优化
- 根据实际显示尺寸准备图片
- 避免使用过大的图片（建议单张图片 < 500KB）
- 可以使用在线工具压缩图片：
  - TinyPNG (https://tinypng.com/)
  - Squoosh (https://squoosh.app/)

### 响应式图片
对于不同屏幕尺寸，可以准备多个版本：

```typescript
export const images = {
  heroDesktop: '@/assets/images/hero-desktop.jpg',
  heroTablet: '@/assets/images/hero-tablet.jpg',
  heroMobile: '@/assets/images/hero-mobile.jpg',
}
```

## 常用图片位置

| 用途 | 配置项 | 默认图片 |
|------|--------|----------|
| Logo | `logo` | logo.svg |
| 网站图标 | `favicon` | favicon.png |
| 首页背景 | `heroBackground` | mh.png |
| 基因组功能图 | `featureGenome` | egg.jpg |
| 分析功能图 | `featureAnalysis` | mh.png |
| 可视化展示图 | `featureVisualization` | screenshot-dashboard.png |

## 故障排除

### 图片不显示？

1. **检查路径是否正确**
   ```typescript
   // ✅ 正确
   '@/assets/images/my-image.jpg'
   
   // ❌ 错误
   '/src/assets/images/my-image.jpg'
   './my-image.jpg'
   ```

2. **检查文件名大小写**
   - `MyImage.jpg` ≠ `myimage.jpg`
   - Windows 不区分大小写，但 Linux/Mac 区分

3. **检查文件是否存在**
   ```bash
   ls src/assets/images/
   ```

4. **清除缓存并重启开发服务器**
   ```bash
   npm run dev
   ```

### 图片加载慢？

1. **压缩图片** - 使用 TinyPNG 等工具
2. **转换为 WebP 格式** - 文件更小
3. **使用懒加载** - 对非首屏图片：
   ```vue
   <img src="..." loading="lazy" alt="...">
   ```

## CSS 背景图片

如果需要在 CSS 中使用图片：

```vue
<style scoped>
.hero-section {
  background-image: url('@/assets/images/mh.png');
  background-size: cover;
  background-position: center;
}
</style>
```

或在 JavaScript 中动态设置：

```vue
<script setup>
import { images } from '@/config/theme.config'
import { computed } from 'vue'

const heroStyle = computed(() => ({
  backgroundImage: `url(${images.heroBackground})`,
}))
</script>

<template>
  <div :style="heroStyle" class="hero">
    <!-- 内容 -->
  </div>
</template>
```

## 主题切换支持

如果需要支持多主题图片：

```typescript
// theme.config.ts
export const images = {
  light: {
    hero: '@/assets/images/hero-light.png',
  },
  dark: {
    hero: '@/assets/images/hero-dark.png',
  }
}
```

---

**最后更新**: 2026-06-14
**维护者**: CottonOGD Frontend Team
