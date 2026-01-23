<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search, DataAnalysis, PieChart, Setting } from '@element-plus/icons-vue'

const searchQuery = ref('')
const router = useRouter()

const performSearch = () => {
  if (searchQuery.value.trim()) {
    // 跳转到搜索结果页面并传递搜索参数
    router.push({
      path: '/tools/id-search/results',
      query: { q: searchQuery.value.trim() }
    })
  }
}
</script>
<template>
  <div class="home">
    <div class="hero-section">
      <div class="container">
        <h1 class="text-center mb-4">Welcome to CottonOGD Website</h1>
        <p class="text-center mb-6">Comprehensive genomic database for cotton research</p>
        
        <!-- 主要搜索框 -->
        <div class="search-box-container">
          <el-input
            v-model="searchQuery"
            placeholder="Enter gene ID, symbol or keyword..."
            clearable
            size="large"
            @keyup.enter="performSearch"
            class="search-input"
          >
            <template #append>
              <el-button type="primary" size="large" @click="performSearch">
                <el-icon><Search /></el-icon>
                Search
              </el-button>
            </template>
          </el-input>
        </div>
      </div>
    </div>
    
    <!-- 功能卡片区域 -->
    <div class="features-section py-8">
      <div class="container">
        <el-row :gutter="20">
          <!-- 浏览功能 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="icon-container">
                <el-icon :size="48" class="text-primary"><DataAnalysis /></el-icon>
              </div>
              <h3 class="mt-3 mb-2">Browse</h3>
              <p class="mb-4">Explore cotton genome data, species information and transcription factors</p>
              <router-link to="/browse/genome">
                <el-button type="primary" plain>Get Started</el-button>
              </router-link>
            </el-card>
          </el-col>
          
          <!-- 可视化功能 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="icon-container">
                <el-icon :size="48" class="text-primary"><PieChart /></el-icon>
              </div>
              <h3 class="mt-3 mb-2">Visualization</h3>
              <p class="mb-4">View genomic data interactively with JBrowse and expression patterns</p>
              <router-link to="/jbrowse">
                <el-button type="primary" plain>Launch JBrowse</el-button>
              </router-link>
            </el-card>
          </el-col>
          
          <!-- 分析工具 -->
          <el-col :span="8">
            <el-card shadow="hover" class="feature-card">
              <div class="icon-container">
                <el-icon :size="48" class="text-primary"><Setting /></el-icon>
              </div>
              <h3 class="mt-3 mb-2">Tools</h3>
              <p class="mb-4">Use various analysis tools for gene function, expression and enrichment</p>
              <router-link to="/tools/id-search">
                <el-button type="primary" plain>Explore Tools</el-button>
              </router-link>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
    
    <!-- 最新研究区域 -->
    <div class="research-section bg-light py-8">
      <div class="container">
        <h2 class="text-center mb-6">Latest Research Highlights</h2>
        <el-row :gutter="20">
          <el-col :span="12">
            <el-card shadow="hover" class="research-card">
              <h4>Genome-Wide Analysis of Cotton Transcription Factors</h4>
              <p class="text-muted">Identification and characterization of transcription factor families across cotton species</p>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card shadow="hover" class="research-card">
              <h4>Comparative Genomics of Gossypium</h4>
              <p class="text-muted">Evolutionary insights from comparative analysis of multiple cotton genomes</p>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
    
    <!-- 数据统计区域 -->
    <div class="stats-section py-8">
      <div class="container">
        <h2 class="text-center mb-6">Database Statistics</h2>
        <el-row :gutter="20">
          <el-col :span="6">
            <el-card shadow="hover" class="stats-card">
              <div class="text-center">
                <el-icon :size="48" class="text-primary mb-2"><DataAnalysis /></el-icon>
                <h3>20,000+</h3>
                <p class="text-muted">Annotated Genes</p>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stats-card">
              <div class="text-center">
                <el-icon :size="48" class="text-primary mb-2"><PieChart /></el-icon>
                <h3>500+</h3>
                <p class="text-muted">Pathways</p>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stats-card">
              <div class="text-center">
                <el-icon :size="48" class="text-primary mb-2"><Setting /></el-icon>
                <h3>20+</h3>
                <p class="text-muted">Analysis Tools</p>
              </div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="hover" class="stats-card">
              <div class="text-center">
                <el-icon :size="48" class="text-primary mb-2"><Search /></el-icon>
                <h3>5,000+</h3>
                <p class="text-muted">Research Papers</p>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
    
    <!-- 快速访问区域 -->
    <div class="quick-access-section bg-light py-8">
      <div class="container">
        <h2 class="text-center mb-6">Quick Access</h2>
        <el-row :gutter="20">
          <el-col :span="6">
            <router-link to="/browse/genome" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="text-center">
                  <el-icon :size="32" class="text-primary mb-2"><DataAnalysis /></el-icon>
                  <h4>Genome Browser</h4>
                  <p class="text-muted">Explore cotton genomes</p>
                </div>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/blastp" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="text-center">
                  <el-icon :size="32" class="text-primary mb-2"><Search /></el-icon>
                  <h4>BLAST Search</h4>
                  <p class="text-muted">Sequence similarity search</p>
                </div>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/tools/go-enrichment" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="text-center">
                  <el-icon :size="32" class="text-primary mb-2"><PieChart /></el-icon>
                  <h4>GO Enrichment</h4>
                  <p class="text-muted">Gene ontology analysis</p>
                </div>
              </el-card>
            </router-link>
          </el-col>
          <el-col :span="6">
            <router-link to="/jbrowse" class="quick-link">
              <el-card shadow="hover" class="quick-link-card">
                <div class="text-center">
                  <el-icon :size="32" class="text-primary mb-2"><Setting /></el-icon>
                  <h4>JBrowse</h4>
                  <p class="text-muted">Interactive genome viewer</p>
                </div>
              </el-card>
            </router-link>
          </el-col>
        </el-row>
      </div>
    </div>
    
    <!-- 新闻公告区域 -->
    <div class="news-section py-8">
      <div class="container">
        <h2 class="text-center mb-6">News & Announcements</h2>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card shadow="hover" class="news-card">
              <template #header>
                <div class="card-header">
                  <span>Latest Update</span>
                  <el-tag type="info" size="small">New</el-tag>
                </div>
              </template>
              <p>Database updated with latest cotton genome annotations and new analysis tools.</p>
              <div class="text-right mt-2">
                <el-button type="text" size="small">Read more</el-button>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover" class="news-card">
              <template #header>
                <div class="card-header">
                  <span>New Publication</span>
                </div>
              </template>
              <p>New research paper published on cotton transcription factors using CottonOGD data.</p>
              <div class="text-right mt-2">
                <el-button type="text" size="small">Read more</el-button>
              </div>
            </el-card>
          </el-col>
          <el-col :span="8">
            <el-card shadow="hover" class="news-card">
              <template #header>
                <div class="card-header">
                  <span>Upcoming Features</span>
                </div>
              </template>
              <p>Coming soon: Enhanced gene expression analysis tools and integrated pathway viewer.</p>
              <div class="text-right mt-2">
                <el-button type="text" size="small">Read more</el-button>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </div>
    </div>
  </div>
</template>

<style scoped>
.home {
  padding-bottom: 2rem;
}

.hero-section {
  padding: 4rem 0;
  background-color: #f8f9fa;
}

.search-box-container {
  max-width: 600px;
  margin: 0 auto;
}

.search-input {
  width: 100%;
}

.features-section {
  background-color: white;
}

.feature-card {
  text-align: center;
  padding: 2rem;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.icon-container {
  height: 80px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.research-card {
  transition: box-shadow 0.3s ease;
}

.research-card:hover {
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.stats-section {
  background-color: white;
}

.stats-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  text-align: center;
  padding: 2rem;
}

.stats-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.quick-access-section {
  background-color: #f8f9fa;
}

.quick-link {
  text-decoration: none;
  color: inherit;
}

.quick-link-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  text-align: center;
  padding: 1.5rem;
}

.quick-link-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.news-section {
  background-color: white;
}

.news-card {
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.news-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
</style>