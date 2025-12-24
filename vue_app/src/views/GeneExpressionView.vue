<template>
  <div class="container mt-4">
    <h2 class="mb-4">Gene Expression Analysis</h2>
    
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="gene_list">Enter gene list (one gene per line or separated by spaces):</label>
        <textarea 
          class="form-control" 
          id="gene_list" 
          v-model="geneList"
          rows="10"
        ></textarea>
        <button 
          type="button" 
          class="btn btn-sm btn-outline-secondary mt-2" 
          @click="fillExample"
        >
          Load Example
        </button>
      </div>
      
      <div class="form-group mt-3">
        <label for="tissue">Select Tissue:</label>
        <select 
          class="form-control" 
          id="tissue" 
          v-model="selectedTissue"
        >
          <option value="">-- All Tissues --</option>
          <!-- Top tissues -->
          <option value="Root">Root</option>
          <option value="Stem">Stem</option>
          <option value="Cotyledon">Cotyledon</option>
          <option value="Leaf">Leaf</option>
          <option value="Pholem">Pholem</option>
          <option value="Sepal">Sepal</option>
          <option value="Bract">Bract</option>
          <option value="Petal">Petal</option>
          <option value="Anther">Anther</option>
          <option value="Stigma">Stigma</option>
          <!-- Bottom left tissues -->
          <option value="0_DPA_ovules">0_DPA_ovules</option>
          <option value="3_DPA_fibers">3_DPA_fibers</option>
          <option value="6_DPA_fibers">6_DPA_fibers</option>
          <option value="9_DPA_fibers">9_DPA_fibers</option>
          <option value="12_DPA_fibers">12_DPA_fibers</option>
          <option value="15_DPA_fibers">15_DPA_fibers</option>
          <option value="18_DPA_fibers">18_DPA_fibers</option>
          <option value="21_DPA_fibers">21_DPA_fibers</option>
          <option value="24_DPA_fibers">24_DPA_fibers</option>
          <!-- Bottom right tissues -->
          <option value="DPA0">DPA0</option>
          <option value="5_DPA_ovules">5_DPA_ovules</option>
          <option value="10_DPA_ovules">10_DPA_ovules</option>
          <option value="20_DPA_ovules">20_DPA_ovules</option>
          <option value="Seed">Seed</option>
        </select>
      </div>
      
      <button type="submit" class="btn btn-primary mt-4">Submit Analysis</button>
      
      <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import httpInstance from '../utils/http'

const router = useRouter()

// 表单数据
const geneList = ref('')
const selectedTissue = ref('')
const error = ref('')

// 填充示例数据
const fillExample = () => {
  const exampleIDs = `Ghjin_A01g000110
Ghjin_A01g000120
Ghjin_A01g000130
Ghjin_A01g000140
Ghjin_A01g000150
Ghjin_A01g000160
Ghjin_A01g000170
Ghjin_A01g000180
Ghjin_A01g000190
`
  geneList.value = exampleIDs
}

// 提交表单
const handleSubmit = async () => {
  error.value = ''
  
  // 验证表单
  if (!geneList.value.trim()) {
    error.value = 'Please enter gene list'
    return
  }
  
  try {
    // 构建查询参数，直接跳转到结果页面
    // 结果页面会在组件挂载时调用API获取数据
    const params = {
      gene_list: geneList.value,
      tissue: selectedTissue.value,
    }
    
    router.push({
      path: '/tools/gene-expression/results',
      query: params
    })
  } catch (err) {
    error.value = 'Submission failed, please try again'
    console.error('Submission failed:', err)
  }
}
</script>

<style scoped>
.form-group {
  margin-bottom: 1rem;
}

.btn-primary {
  background-color: #007bff;
  border-color: #007bff;
}

.btn-primary:hover {
  background-color: #0069d9;
  border-color: #0062cc;
}
</style>