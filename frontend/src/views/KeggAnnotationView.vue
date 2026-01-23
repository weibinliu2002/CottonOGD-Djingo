<template>
  <div class="container mt-4">
    <h2>KEGG Annotation Search</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>KEGG Annotation Search</span>
        </div>
      </template>
      
      <el-form @submit.prevent="submitForm" label-width="350px">
        <el-form-item label="Enter Gene IDs (one per line or space/comma separated)">
          <el-input
            type="textarea"
            :rows="5"
            v-model="geneIds"
            placeholder="Please enter gene IDs"
            :disabled="isLoading"
          />
          <div class="mt-2">
            <el-button 
              type="info" 
              size="small" 
              @click="fillExample"
              :disabled="isLoading"
            >
              load example
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item>
          <div class="d-flex justify-content-end">
            <el-button 
              type="primary" 
              native-type="submit"
              :loading="isLoading"
            >
              Search
            </el-button>
          </div>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../utils/http'
import { ElMessage } from 'element-plus'

const geneIds = ref('')
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
Kirkii_Juiced.00g000230`;
  geneIds.value = exampleIDs;
}

const submitForm = async () => {
  if (!geneIds.value.trim()) {
    ElMessage.error('Please enter gene IDs');
    return;
  }

  isLoading.value = true
  try {
      // 使用全局axios实例调用后端API
      const responseData = await axios.post('/tools/kegg_annotation/api/start/', {
        gene_id: geneIds.value
      })

      if (responseData.status === 'success' && responseData.task_id) {
        // 使用任务ID跳转到结果页面
        router.push({
          path: '/tools/kegg-annotation/results',
          query: {
            task_id: responseData.task_id
          }
        })
      } else {
        ElMessage.error('Error: ' + (responseData.error || 'Failed to get task ID'));
      }
  } catch (error) {
    console.error('Error submitting form:', error)
    ElMessage.error('Error submitting form: ' + (error.message || 'Unknown error'));
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

.mt-4 {
  margin-top: 1.5rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.mt-2 {
  margin-top: 0.5rem;
}

.d-flex {
  display: flex;
}

.justify-content-end {
  justify-content: flex-end;
}

.card-header {
  font-size: 16px;
  font-weight: 500;
}
</style>