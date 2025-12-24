<template>
  <div class="container mt-4">
    <h2 class="mb-4">GO富集分析</h2>
    
    <form @submit.prevent="handleSubmit">
      <div class="form-group">
        <label for="gene_list">输入基因列表 (每行一个基因或空格分隔):</label>
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
          load example
        </button>
      </div>
      
      <div class="row mt-3">
        <div class="col-md-6">
          <div class="form-group">
            <label for="p_value">P值阈值:</label>
            <input 
              type="number" 
              class="form-control" 
              id="p_value" 
              v-model.number="pValue"
              min="0.0001" 
              max="1" 
              step="0.0001"
              required
            >
          </div>
        </div>
        <div class="col-md-6">
          <div class="form-group">
            <label for="q_value">Q值阈值:</label>
            <input 
              type="number" 
              class="form-control" 
              id="q_value" 
              v-model.number="qValue"
              min="0.0001" 
              max="1" 
              step="0.0001"
              required
            >
          </div>
        </div>
      </div>
      
      <div class="form-group mt-3">
        <label for="per_page">每页显示结果数:</label>
        <select 
          class="form-control" 
          id="per_page" 
          v-model.number="perPage"
        >
          <option value="5">5</option>
          <option value="10" selected>10</option>
          <option value="25">25</option>
          <option value="50">50</option>
        </select>
      </div>
      
      <button type="submit" class="btn btn-primary mt-4">提交分析</button>
      
      <div v-if="error" class="alert alert-danger mt-3">{{ error }}</div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, getCurrentInstance } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 获取全局属性
const app = getCurrentInstance()
const $http = app?.appContext.config.globalProperties.$http

// 表单数据
const geneList = ref('')
const pValue = ref(0.05)
const qValue = ref(0.05)
const perPage = ref(10)
const error = ref('')

// 填充示例数据
const fillExample = () => {
  const exampleIDs = `Kirkii_Juiced.00g000010
Kirkii_Juiced.00g000020
Kirkii_Juiced.00g000030
Kirkii_Juiced.00g000040
Kirkii_Juiced.00g000050
Kirkii_Juiced.00g000060
Kirkii_Juiced.00g000070
Kirkii_Juiced.00g000080
Kirkii_Juiced.00g000090
Kirkii_Juiced.00g000100
Kirkii_Juiced.00g000110
Kirkii_Juiced.00g000120
Kirkii_Juiced.00g000130
Kirkii_Juiced.00g000140
Kirkii_Juiced.00g000150
Kirkii_Juiced.00g000160
Kirkii_Juiced.00g000170
Kirkii_Juiced.00g000180
Kirkii_Juiced.00g000190
Kirkii_Juiced.00g000200
Kirkii_Juiced.00g000210
Kirkii_Juiced.00g000220
Kirkii_Juiced.00g000230`
  geneList.value = exampleIDs
}

// 提交表单
const handleSubmit = async () => {
  error.value = ''
  
  // 验证表单
  if (!geneList.value.trim()) {
    error.value = '请输入基因列表'
    return
  }
  
  try {
    if (!$http) {
      throw new Error('未找到全局axios实例')
    }
    
    // 使用全局的axios实例提交数据到正确的API端点
    const response = await $http.post('/tools/go_enrichment/api/start/', {
      gene_list: geneList.value,
      p_value: pValue.value,
      q_value: qValue.value,
      per_page: perPage.value
    })
    
    const data = response.data
    
    if (data.status === 'success') {
      // 使用后端返回的task_id跳转到结果页面
      router.push({
        path: '/tools/go-enrichment/results',
        query: { task_id: data.task_id }
      })
    } else {
      error.value = data.error || '提交失败'
    }
  } catch (err: any) {
    error.value = '提交失败，请重试'
    console.error('提交失败:', err)
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