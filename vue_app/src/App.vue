<template>
  <div class="app">
    <div id="head-container">
      <div class="head-content">
        <img src="@/assets/images/egg.jpg" alt="Logo" style="height:90px; width:100px;">
        <div class="site-title">
          <span class="main-title">
            CottonOGD
          </span>
          <span class="sub-title">
            ——  a comprehensive cotton orthogroups database
          </span>
        </div>
      </div>
    </div>
    <!-- 导航栏 -->
    <nav class="navbar navbar-expand-lg custom-navbar">
      <div class="container">
        <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
          <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="navbarNav">
          <ul class="navbar-nav">
            <li class="nav-item">
              <router-link class="nav-link" to="/" exact-active-class="active">Home</router-link>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" id="BrowseDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">Browse</a>
              <ul class="dropdown-menu" aria-labelledby="BrowseDropdown">
                <li><router-link class="dropdown-item" to="/browse/genome">Genome</router-link></li>
                <li><router-link class="dropdown-item" to="/browse/species">Species</router-link></li>
                <li><router-link class="dropdown-item" to="/browse/tf">TF</router-link></li>
              </ul>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/jbrowse" exact-active-class="active">Jbrowse</router-link>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" id="toolsDropdown" role="button" data-bs-toggle="dropdown" aria-expanded="false">Tools</a>
              <ul class="dropdown-menu" aria-labelledby="toolsDropdown">
                <li><router-link class="dropdown-item" to="/tools/id-search">Search by GeneID</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/blastp">blastp</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/go-enrichment">go_enrichment</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/go-annotation">go_annotation</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/kegg-annotation">kegg_annotation</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/kegg-enrichment">kegg_enrichment</router-link></li>
               <!--<router-link class="dropdown-item" to="/tools/heatmap">heatmap</router-link></li>-->
                <li><router-link class="dropdown-item" to="/tools/gene-expression">gene_expression</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/gene-expression-efp">gene_expression_in_eFP</router-link></li>
              </ul>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/download">Download</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/about-us">About</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/contact-us">Contact us</router-link>
            </li>
          </ul>
        </div>
      </div>
    </nav>
    
    <!-- 主要内容 -->
    <main class="container">
      <router-view />
    </main>
    
    <!-- 加载遮罩 -->
    <div v-if="isLoading" class="loading-overlay">
      <div class="loading-content">
        <div class="spinner-border text-primary" role="status">
          <span class="visually-hidden">Loading...</span>
        </div>
        <div class="mt-3">正在检索中...</div>
      </div>
    </div>
    
    <!-- 底部区域 -->
    <div class="footer-section">
      <!-- 页脚 -->
      <footer>
        <div class="container">
          <p class="mb-0">CottonOGD Website &copy; 2025</p>
        </div>
      </footer>
    </div>
    
    <!-- 回到顶部组件 -->
    <el-backtop
      :visibility-height="200"
      :right="40"
      :bottom="40"
      target=".app"
    >
      <template #default>
        <div class="backtop-content">
          <el-icon class="backtop-icon"><ArrowUp /></el-icon>
        </div>
      </template>
    </el-backtop>
  </div>
</template>

<script setup>
import { ref, provide } from 'vue'
import { ArrowUp } from '@element-plus/icons-vue'

// 定义全局加载状态
const isLoading = ref(false)

// 定义加载状态管理方法
const showLoading = () => {
  isLoading.value = true
}

const hideLoading = () => {
  isLoading.value = false
}

// 提供全局加载状态和方法
provide('isLoading', isLoading)
provide('showLoading', showLoading)
provide('hideLoading', hideLoading)
</script>

<style>
/* 全局样式 */
/* 样式通过main.js引入，这里不再重复导入 */

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 头部容器样式 */
#head-container {
  margin-top: 30px;
  background-color: #466686;
  width: 100%;
  height: 130px;
}

/* 头部内容容器 */
.head-content {
  max-width: 1400px;
  margin: 0 auto;
  height: 100%;
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 0 30px;
}

/* 网站标题样式 */
.site-title {
  flex-direction: column;
  justify-content: center;
  line-height: 1.3;
  gap: 30px;
}

/* 主标题样式 */
.main-title {
  font-size: 42px;
  font-weight: 700;
  color: #000000;
  letter-spacing: 1px;
  text-shadow: 1px 2px 4px rgba(0,0,0,0.3);
}

/* 副标题样式 */
.sub-title {
  font-size: 22px;
  font-weight: 400;
  color: #000000;
  margin-top: 6px;
  letter-spacing: 0.5px;
}

/* 自定义导航栏 */
.custom-navbar {
  background-color: #7297bd;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

/* 导航链接样式 */
.nav-link {
  color: #ffffff !important;
  transition: color 0.3s ease;
}

.nav-link:hover,
.nav-link.active {
  color: #f0f0f0 !important;
}

/* 下拉菜单样式 */
.dropdown-menu {
  background-color: #7297bd;
  border: none;
  border-radius: 0;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.dropdown-item {
  color: #ffffff;
  transition: background-color 0.3s ease;
}

.dropdown-item:hover,
.dropdown-item:focus {
  background-color: #5a81a8;
  color: #ffffff;
}

/* 图片行样式 */
.image-row {
  display: flex;
  overflow-x: auto;
  white-space: nowrap;
}

.image-tile {
  flex: 0 0 auto;
  margin-right: 10px;
}

.image-tile img {
  max-width: 100%;
  height: auto;
}

/* 底部样式 */
.footer-section {
  margin-top: 30px;
}

footer {
  padding: 20px 0;
  text-align: center;
  background-color: #85a7c9;
  color: #ffffff;
}

/* 响应式容器 */
.container {
  width: 100%;
  padding-right: 15px;
  padding-left: 15px;
  margin-right: auto;
  margin-left: auto;
}

/* 回到顶部按钮样式 */
.backtop-content {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background-color: #7297bd;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
  transition: all 0.3s ease;
}

.backtop-content:hover {
  background-color: #5a81a8;
  transform: scale(1.1);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.3);
}

.backtop-icon {
  font-size: 20px;
}

/* 加载遮罩样式 */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 9999;
  backdrop-filter: blur(2px);
}

.loading-content {
  text-align: center;
  color: #333;
  font-size: 18px;
  font-weight: 500;
}

.spinner-border {
  width: 4rem;
  height: 4rem;
  border-width: 0.3rem;
}
</style>