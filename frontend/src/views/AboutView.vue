<template>
  <div class="container mt-4">
    <div class="page-header">
      <h1 class="page-title">About OGD</h1>
      <p class="page-description">OGD is a platform for exploring and analyzing genetic data.</p>
    </div>
    <el-card>
      <h2>About Our Platform</h2>
      <p>OGD (Online Genome Database) is designed to provide researchers with a comprehensive set of tools for genomic data analysis and visualization.</p>
      <h3>Key Features</h3>
      <ul>
        <li>Genome browsing and exploration</li>
        <li>Gene expression analysis</li>
        <li>Functional annotation tools</li>
        <li>Comparative genomics</li>
        <li>Data download capabilities</li>
      </ul>
    </el-card>
  </div>
</template>

<script>
export default {
  name: 'AboutView'
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: left;
  margin-bottom: 30px;
}

.page-title {
  font-size: 36px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.page-description {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  max-width: 800px;
  margin: 0;
}

ul {
  margin-left: 20px;
}
</style>