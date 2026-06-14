# CottonOGD 现代化设计升级

## 🎨 设计亮点

### 1. 动态背景轮播 (Hero Section)
- **渐变背景自动切换** - 每8秒平滑过渡到下一个渐变色
- **粒子动画效果** - 20个浮动粒子营造科技感
- **背景指示器** - 可点击切换当前背景
- **滚动提示** - 引导用户向下浏览

### 2. 现代化搜索框
- **玻璃态效果** - backdrop-filter blur 半透明模糊
- **圆角设计** - 20px 大圆角更现代
- **阴影层次** - 深度感强的多层阴影
- **高级搜索面板** - 可折叠的筛选条件

### 3. 数据统计卡片
- **渐变图标** - 每个统计项独特的渐变色
- **悬浮动画** - 鼠标悬停时卡片上移 + 阴影加深
- **数字突出** - 36px 粗体数字强调数据
- **响应式网格** - 自适应不同屏幕尺寸

### 4. 功能特性卡片 (带图片)
- **图片展示** - 使用您现有的图片资源
  - `egg.jpg` - 基因组浏览卡片
  - `mh.png` - 分析工具卡片  
  - `screenshot-dashboard.png` - 可视化卡片
- **图片缩放** - 悬停时图片放大 1.05 倍
- **渐变遮罩** - 图片底部蓝色渐变 overlay
- **彩色图标** - 每个功能独特的图标颜色
- **行动链接** - 带箭头的交互按钮

## 🖼️ 图片使用说明

### 当前使用的图片
```typescript
// Hero 背景（动态渐变，无需图片）
bgGradients = [渐变1, 渐变2, 渐变3]

// 功能卡片图片
- egg.jpg → 基因组浏览卡片
- mh.png → 分析工具卡片
- screenshot-dashboard.png → 可视化工具卡片
```

### 如何更换图片

#### 方法一：直接替换文件
1. 准备新图片（建议尺寸：800x400px）
2. 放到 `src/assets/images/` 目录
3. 覆盖同名文件即可

#### 方法二：修改引用路径
编辑 `HomeView.vue` 第 175、182、189 行：
```vue
<div class="card-image" style="background-image: url('@/assets/images/YOUR_IMAGE.jpg')">
```

### 推荐的图片规格
- **格式**: JPG/PNG/WebP
- **尺寸**: 800x400px (2:1 比例)
- **文件大小**: < 200KB
- **主题**: 与功能相关的科研图像

## ✨ 动画效果清单

### CSS Animations
1. **float-up** - 粒子从下往上飘浮
2. **bounce** - 滚动提示上下跳动
3. **scroll** - 鼠标滚轮动画
4. **fade-in** - 内容淡入效果
5. **slide-in** - 卡片滑入效果（错开延迟）

### Transitions
1. **background 2s** - 背景渐变过渡
2. **transform 0.3-0.4s** - 悬浮动画
3. **scale(1.05)** - 图片放大
4. **translateY(-8/-12px)** - 卡片上移

## 🎯 配色方案

### 主色调
```css
--primary-blue: #3a6ea5    /* 品牌蓝 */
--light-blue: #7297bd      /* 浅蓝 */
--dark-blue: #2f5f94       /* 深蓝 */
```

### 渐变色
```css
/* 蓝色渐变（统计卡片） */
gradient-blue: linear-gradient(135deg, #3a6ea5, #7297bd)

/* 绿色渐变（基因数据） */
gradient-green: linear-gradient(135deg, #52c41a, #95de64)

/* 橙色渐变（正交组） */
gradient-orange: linear-gradient(135deg, #ff7b29, #ffa940)

/* 紫色渐变（文献） */
gradient-purple: linear-gradient(135deg, #722ed1, #b37feb)
```

## 📱 响应式设计

### 断点
- **Desktop**: > 768px (完整布局)
- **Mobile**: ≤ 768px (单列布局)

### 移动端优化
- Hero 标题缩小 (56px → 36px)
- 搜索框垂直排列
- 统计卡片单列显示
- 功能卡片单列显示

## 🔧 自定义指南

### 修改背景轮播速度
编辑 `HomeView.vue` 第 20 行：
```typescript
}, 8000) // ← 改为其他毫秒数，如 5000 = 5秒
```

### 修改背景数量/颜色
编辑第 13-17 行：
```typescript
const bgGradients = [
  'linear-gradient(...)', // 背景1
  'linear-gradient(...)', // 背景2
  'linear-gradient(...)', // 背景3
  // 添加更多...
]
```

### 禁用背景轮播
删除或注释掉第 22-27 行：
```typescript
// onMounted(() => { ... })
// onUnmounted(() => { ... })
```

### 修改粒子数量
编辑第 79 行：
```vue
v-for="n in 20" <!-- ← 改为其他数字，如 10 或 30 -->
```

## 🚀 性能优化建议

### 图片优化
1. 使用 WebP 格式（比 JPG 小 30%）
2. 压缩图片至 < 200KB
3. 考虑使用懒加载（对非首屏图片）

### CSS 优化
- 已使用 `will-change` 属性优化动画
- 使用 CSS transform 而非 top/left
- 避免重排（reflow）操作

## 📊 设计对比

### 重构前
- ❌ 静态单色背景
- ❌ 简单列表布局
- ❌ 无动画效果
- ❌ 图片未充分利用

### 重构后
- ✅ 动态渐变背景轮播
- ✅ 现代化卡片布局
- ✅ 丰富的交互动画
- ✅ 图片完美整合到功能卡片
- ✅ 玻璃态设计语言
- ✅ 响应式适配移动端

---

**更新时间**: 2026-06-14  
**设计风格**: Modern Scientific / Glassmorphism  
**技术栈**: Vue 3 + Element Plus + CSS3 Animations
