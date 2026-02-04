<template>
  <div class="app">
    <!-- 顶部信息栏 -->
    <div class="top-info-bar">
      <div class="container">
        <div class="top-info-content">
          <div class="info-left">
            <span class="database-status">Database version: v1.0 | Last updated: 2025-01-29</span>
          </div>
          <div class="info-right">
            <!-- 语言切换 -->
            <div class="language-selector">
              <select 
                :value="currentLanguage" 
                @change="(e) => handleLanguageChange(e.target.value)"
                class="language-select"
              >
                <option value="en-US">English</option>
                <option value="zh-CN">中文</option>
              </select>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 头部容器 -->
    <header class="header">
      <div class="container">
        <div class="header-inner">
          <!-- Logo和标题 -->
          <div class="header-brand">
            <div class="logo-container">
              <img src="@/assets/images/favicon.png" alt="CottonOGD Logo" class="logo">
            </div>
            <div class="brand-text">
              <h1 class="brand-title">CottonOGD</h1>
              <p class="brand-subtitle">Cotton Orthogroups Database</p>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- 导航栏 -->
    <nav class="main-nav">
      <div class="container">
        <div class="nav-inner">
          <!-- 导航链接 -->
          <ul class="nav-menu">
            <li class="nav-item">
              <router-link class="nav-link" to="/" exact-active-class="active">Home</router-link>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                Browse
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/browse/tf">Transcription Factors</router-link></li>
                <li><router-link class="dropdown-item" to="/browse/tr">Transposons</router-link></li>
              </ul>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/jbrowse">JBrowser</router-link>
            </li>
            <li class="nav-item dropdown">
              <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">
                Tools
              </a>
              <ul class="dropdown-menu">
                <li><router-link class="dropdown-item" to="/tools/id-search">Gene ID Search</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/blastp">BLASTP</router-link></li>

                <li><router-link class="dropdown-item" to="/tools/go-annotation">GO Annotation</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/kegg-annotation">KEGG Annotation</router-link></li>

                <li><router-link class="dropdown-item" to="/tools/go-enrichment">GO Enrichment</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/kegg-enrichment">KEGG Enrichment</router-link></li>
    
                <li><router-link class="dropdown-item" to="/tools/gene-expression">Gene Expression</router-link></li>
                <li><router-link class="dropdown-item" to="/tools/gene-expression-efp">Gene Expression (eFP)</router-link></li>
      
                <li><router-link class="dropdown-item" to="/tools/primer-design">Primer Design</router-link></li>
              </ul>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/download">Download</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/about-us">About</router-link>
            </li>
            <li class="nav-item">
              <router-link class="nav-link" to="/contact-us">Contact</router-link>
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
        <div class="mt-3">Searching...</div>
      </div>
    </div>
    
    <!-- 底部区域 -->
    <div class="footer-section">
      <!-- 页脚 -->
      <footer>
        <div class="container">
          <div class="footer-content">
            <div class="footer-column">
              <h4>Quick Links</h4>
              <ul>
                <li><router-link to="/">Home</router-link></li>
                <li><router-link to="/jbrowse">JBrowse</router-link></li>
                <li><router-link to="/download">Download</router-link></li>
                <li><router-link to="/about-us">About Us</router-link></li>
              </ul>
            </div>
            <div class="footer-column">
              <h4>Tools</h4>
              <ul>
                <li><router-link to="/tools/id-search">Gene ID Search</router-link></li>
                <li><router-link to="/tools/blastp">BLASTP</router-link></li>
                <li><router-link to="/tools/go-enrichment">GO Enrichment</router-link></li>
                <li><router-link to="/tools/primer-design">Primer Design</router-link></li>
              </ul>
            </div>
            <div class="footer-column">
              <h4>Contact</h4>
              <!--
              <ul>
                <li><i class="fas fa-envelope"></i> cottonogd@example.com</li>
                <li><i class="fas fa-phone"></i> +86 123 4567 8910</li>
                <li><i class="fas fa-map-marker-alt"></i> Cotton Research Institute</li>
              </ul>-->
            </div>
            <div class="footer-column">
              <h4>About CottonOGD</h4>
              <p>CottonOGD is a comprehensive database for cotton orthogroups, providing researchers with valuable resources for cotton genomics research.</p>
            </div>
          </div>
          <div class="footer-bottom">
            <p class="mb-0">© 2025 CottonOGD. All rights reserved.</p>
          </div>
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
import { ref, provide, onMounted, computed } from 'vue'
import { ArrowUp } from '@element-plus/icons-vue'
import httpInstance from './utils/http.js'
import { useRouter } from 'vue-router'

const router = useRouter()

// 定义全局加载状态
const isLoading = ref(false)

// 搜索相关
const searchQuery = ref('')

// 当前语言
const currentLanguage = ref(localStorage.getItem('language') || 'en-US')

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

// 语言切换方法
const handleLanguageChange = (lang) => {
  currentLanguage.value = lang
  localStorage.setItem('language', lang)
  // 这里可以添加实际的语言切换逻辑
  console.log('Switched to language:', lang)
}

// 搜索方法
const performSearch = () => {
  if (searchQuery.value.trim()) {
    router.push({
      path: '/tools/id-search',
      query: { query: searchQuery.value.trim() }
    })
  }
}

// 组件挂载时自动登录
onMounted(() => {
  httpInstance.post('/CottonOGD_api/login/')
})
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

/* 顶部信息栏 */
.top-info-bar {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  padding: 8px 0;
  font-size: 14px;
  color: #6c757d;
}

.top-info-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.language-selector {
  display: flex;
  gap: 5px;
}

.language-select {
  background-color: white;
  border: 1px solid #ced4da;
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s ease;
  min-width: 100px;
}

.language-select:hover {
  border-color: #466686;
}

.language-select:focus {
  outline: none;
  border-color: #466686;
  box-shadow: 0 0 0 0.2rem rgba(70, 102, 134, 0.25);
}

/* 头部样式 */
.header {
  background-color: #466686;
  padding: 20px 0;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.header-inner {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  flex-wrap: wrap;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 20px;
}

.logo-container {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background-color: white;
  border-radius: 10px;
  box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}

.logo {
  height: 60px;
  width: auto;
}

.brand-text {
  display: flex;
  flex-direction: column;
  text-align: left;
}

.brand-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: white;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 2px rgba(0,0,0,0.2);
}

.brand-subtitle {
  margin: 3px 0 0 0;
  font-size: 12px;
  color: rgba(255,255,255,0.9);
  font-weight: 400;
}

/* 导航栏样式 */
.main-nav {
  background-color: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  position: sticky;
  top: 0;
  z-index: 1000;
}

.nav-inner {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.nav-menu {
  display: flex;
  list-style: none;
  margin: 0;
  padding: 0;
  gap: 0;
  background-color: #f8f9fa;
  flex-wrap: wrap;
  justify-content: flex-start;
}

.nav-item {
  position: relative;
}

.nav-link {
  display: block;
  color: #466686 !important;
  padding: 14px 18px !important;
  text-decoration: none;
  font-weight: 500;
  transition: all 0.3s ease;
  border-radius: 0;
  border-right: 1px solid #e9ecef;
}

.nav-link:hover,
.nav-link.active {
  background-color: #e9ecef !important;
  color: #3a5470 !important;
}

/* 下拉菜单样式 */
.dropdown-menu {
  position: absolute;
  top: 100%;
  left: 0;
  background-color: white;
  border: 1px solid #e9ecef;
  border-radius: 0 0 4px 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  padding: 4px 0;
  margin: 0;
  min-width: 200px;
  z-index: 1000;
}

.dropdown-header {
  color: #6c757d;
  padding: 6px 16px;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.dropdown-divider {
  height: 1px;
  background-color: #e9ecef;
  margin: 4px 0;
}

.dropdown-item {
  color: #466686;
  padding: 8px 16px;
  text-decoration: none;
  display: block;
  transition: all 0.3s ease;
  font-size: 13px;
}

.dropdown-item:hover,
.dropdown-item:focus {
  background-color: #e9ecef;
  color: #3a5470;
}

/* 响应式导航 */
@media (max-width: 992px) {
  .header-inner {
    flex-direction: column;
    text-align: center;
  }

  .header-brand {
    flex-direction: column;
    gap: 15px;
  }

  .brand-text {
    text-align: center;
  }

  .nav-menu {
    justify-content: flex-start;
  }

  .nav-link {
    padding: 10px 14px !important;
    font-size: 13px;
  }
}

@media (max-width: 768px) {
  .brand-title {
    font-size: 26px;
  }

  .brand-subtitle {
    font-size: 12px;
  }

  .logo-container {
    width: 60px;
    height: 60px;
  }

  .logo {
    height: 40px;
  }

  .header {
    padding: 20px 0;
  }

  .nav-menu {
    flex-direction: column;
    gap: 0;
  }

  .nav-link {
    border-right: none;
    border-bottom: 1px solid #e9ecef;
  }

  .dropdown-menu {
    position: static;
    border-radius: 0;
    box-shadow: none;
    border-left: 3px solid #e9ecef;
  }

  .dropdown-item {
    padding-left: 24px;
  }
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
  margin-top: 50px;
  background-color: #f8f9fa;
  border-top: 1px solid #e9ecef;
}

footer {
  padding: 40px 0;
  color: #6c757d;
}

.footer-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 30px;
  margin-bottom: 30px;
}

.footer-column h4 {
  color: #466686;
  margin-bottom: 15px;
  font-size: 16px;
  font-weight: 600;
}

.footer-column ul {
  list-style: none;
  padding: 0;
  margin: 0;
}

.footer-column ul li {
  margin-bottom: 10px;
}

.footer-column ul li a {
  color: #6c757d;
  text-decoration: none;
  transition: color 0.3s ease;
}

.footer-column ul li a:hover {
  color: #466686;
}

.footer-column ul li i {
  margin-right: 8px;
  color: #7297bd;
}

.footer-bottom {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
  font-size: 14px;
}

/* 响应式容器 */
.container {
  width: 100%;
  max-width: 1400px;
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

/* 响应式设计 */
@media (max-width: 992px) {
  .head-content {
    flex-direction: column;
    text-align: center;
    gap: 20px;
  }

  .search-section {
    max-width: 100%;
    width: 100%;
  }

  .navbar-nav {
    gap: 0;
  }

  .nav-link {
    padding: 10px 15px !important;
  }
}

@media (max-width: 768px) {
  .top-info-content {
    flex-direction: column;
    gap: 10px;
    text-align: center;
  }

  .site-title h1 {
    font-size: 32px;
  }

  .site-title p {
    font-size: 16px;
  }

  .footer-content {
    grid-template-columns: 1fr;
    gap: 20px;
  }
}
</style>