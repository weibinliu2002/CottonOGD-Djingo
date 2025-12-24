<script>
export default {
  name: 'HomeView',
  data() {
    return {
      searchQuery: ''
    }
  },
  methods: {
    performSearch() {
      if (this.searchQuery.trim()) {
        // 跳转到搜索结果页面并传递搜索参数
        this.$router.push({
          path: '/tools/id-search/results',
          query: { q: this.searchQuery.trim() }
        })
      }
    }
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
          <div class="input-group">
            <input 
              type="text" 
              class="form-control form-control-lg" 
              placeholder="Enter gene ID, symbol or keyword..."
              v-model="searchQuery"
              @keyup.enter="performSearch"
            >
            <button class="btn btn-primary btn-lg" @click="performSearch">
              <i class="fas fa-search"></i> Search
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 功能卡片区域 -->
    <div class="features-section py-8">
      <div class="container">
        <div class="row">
          <!-- 浏览功能 -->
          <div class="col-md-4 mb-4">
            <div class="feature-card h-100">
              <div class="icon-container">
                <i class="fas fa-database fa-3x text-primary"></i>
              </div>
              <h3 class="mt-3 mb-2">Browse</h3>
              <p class="mb-4">Explore cotton genome data, species information and transcription factors</p>
              <router-link to="/browse/genome" class="btn btn-outline-primary">
                Get Started
              </router-link>
            </div>
          </div>
          
          <!-- 可视化功能 -->
          <div class="col-md-4 mb-4">
            <div class="feature-card h-100">
              <div class="icon-container">
                <i class="fas fa-chart-line fa-3x text-primary"></i>
              </div>
              <h3 class="mt-3 mb-2">Visualization</h3>
              <p class="mb-4">View genomic data interactively with JBrowse and expression patterns</p>
              <router-link to="/jbrowse" class="btn btn-outline-primary">
                Launch JBrowse
              </router-link>
            </div>
          </div>
          
          <!-- 分析工具 -->
          <div class="col-md-4 mb-4">
            <div class="feature-card h-100">
              <div class="icon-container">
                <i class="fas fa-tools fa-3x text-primary"></i>
              </div>
              <h3 class="mt-3 mb-2">Tools</h3>
              <p class="mb-4">Use various analysis tools for gene function, expression and enrichment</p>
              <router-link to="/tools/id-search" class="btn btn-outline-primary">
                Explore Tools
              </router-link>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 最新研究区域 -->
    <div class="research-section bg-light py-8">
      <div class="container">
        <h2 class="text-center mb-6">Latest Research Highlights</h2>
        <div class="row">
          <div class="col-md-6 mb-4">
            <div class="research-card bg-white rounded-lg shadow-sm p-4">
              <h4>Genome-Wide Analysis of Cotton Transcription Factors</h4>
              <p class="text-muted">Identification and characterization of transcription factor families across cotton species</p>
            </div>
          </div>
          <div class="col-md-6 mb-4">
            <div class="research-card bg-white rounded-lg shadow-sm p-4">
              <h4>Comparative Genomics of Gossypium</h4>
              <p class="text-muted">Evolutionary insights from comparative analysis of multiple cotton genomes</p>
            </div>
          </div>
        </div>
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

.features-section {
  background-color: white;
}

.feature-card {
  text-align: center;
  padding: 2rem;
  border: 1px solid #e9ecef;
  border-radius: 8px;
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
</style>