<template>
  <div class="container mt-4">
    <h2 class="mb-4">GO注释</h2>
    
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 表单数据
const geneList = ref('')
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
Kirkii_Juiced.00g000100`
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
  
  // 构建查询参数
  const params = {
    gene_list: geneList.value,
    per_page: perPage.value
  }
  
  try {
    // 在实际项目中，这里应该调用API进行数据处理
    // 这里我们直接跳转到结果页面，并传递参数
    router.push({
      path: '/tools/go-annotation/results',
      query: params
    })
  } catch (err) {
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