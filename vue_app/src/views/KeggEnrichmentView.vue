<template>
  <div class="container mt-4">
    <h2>KEGG通路富集分析</h2>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="gene_list">输入基因ID（每行一个或空格/逗号分隔）:</label>
        <textarea 
          id="gene_list" 
          v-model="geneList"
          class="form-control" 
          rows="10" 
          placeholder="请在此输入基因ID..."
          :disabled="isLoading"
        ></textarea>
        <button 
          type="button" 
          class="btn btn-sm btn-outline-secondary mt-2" 
          @click="fillExample"
          :disabled="isLoading"
        >
          加载示例
        </button>
      </div>
      
      <div class="row g-3 mt-3">
        <div class="col-md-6">
          <label for="p_value_threshold" class="form-label">P值阈值:</label>
          <input 
            type="number" 
            id="p_value_threshold" 
            v-model.number="pValueThreshold"
            class="form-control" 
            min="0" 
            max="1" 
            step="0.001"
            :disabled="isLoading"
          >
        </div>
        
        <div class="col-md-6">
          <label for="q_value_threshold" class="form-label">Q值阈值:</label>
          <input 
            type="number" 
            id="q_value_threshold" 
            v-model.number="qValueThreshold"
            class="form-control" 
            min="0" 
            max="1" 
            step="0.001"
            :disabled="isLoading"
          >
        </div>
      </div>
      
      <div class="d-flex justify-content-end mt-3">
        <button 
          type="submit" 
          class="btn btn-primary"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          <span v-else>提交</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../utils/http'

const geneList = ref('')
const pValueThreshold = ref(0.05)
const qValueThreshold = ref(0.05)
const isLoading = ref(false)
const router = useRouter()

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
Kirkii_Juiced.00g000230
Kirkii_Juiced.00g000240
Kirkii_Juiced.00g000250
Kirkii_Juiced.00g000260
Kirkii_Juiced.00g000270
Kirkii_Juiced.00g000280
Kirkii_Juiced.00g000290
Kirkii_Juiced.00g000300`;
  geneList.value = exampleIDs;
}

const submitForm = async () => {
  if (!geneList.value.trim()) {
    alert('请输入基因ID');
    return;
  }

  if (pValueThreshold.value < 0 || pValueThreshold.value > 1) {
    alert('P值阈值必须在0到1之间');
    return;
  }

  if (qValueThreshold.value < 0 || qValueThreshold.value > 1) {
    alert('Q值阈值必须在0到1之间');
    return;
  }

  isLoading.value = true
  try {
    // 使用配置好的axios实例调用后端API
    // 类型断言：由于axios拦截器已经返回了response.data，所以直接断言为any类型
    const responseData: any = await axios.post('/tools/kegg_enrichment/api/start/', {
      gene_list: geneList.value,
      p_value_threshold: pValueThreshold.value
    })

    // 检查API返回的数据
    if (responseData && responseData.status === 'success' && responseData.task_id) {
      // 使用任务ID跳转到结果页面
      router.push({
        path: '/tools/kegg-enrichment/results',
        query: {
          task_id: responseData.task_id
        }
      })
    } 
  } catch (error: any) {
    console.error('提交表单时出错:', error)
    alert('提交表单时出错: ' + (error.message || '未知错误'))
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.container {
  max-width: 900px;
  margin: 0 auto;
}

.form-group {
  margin-bottom: 1.5rem;
}

textarea {
  resize: vertical;
  min-height: 200px;
}

.form-row {
  margin-bottom: 1.5rem;
}

.btn-primary {
  background-color: #007bff;
  border-color: #007bff;
}

.btn-primary:hover {
  background-color: #0056b3;
  border-color: #0056b3;
}

.btn-outline-secondary {
  border-color: #6c757d;
  color: #6c757d;
}

.btn-outline-secondary:hover {
  background-color: #6c757d;
  color: white;
}
</style>