<template>
  <div class="container mt-4">
    <h2>KEGG Annotation Search</h2>
    <form @submit.prevent="submitForm">
      <div class="form-group">
        <label for="gene_id">Enter Gene IDs (one per line or space/comma separated):</label>
        <textarea 
          id="gene_id" 
          v-model="geneIds"
          class="form-control" 
          rows="5" 
          :disabled="isLoading"
        ></textarea>
        <button 
          type="button" 
          class="btn btn-sm btn-outline-secondary mt-2" 
          id="fillExample"
          @click="fillExample"
          :disabled="isLoading"
        >
          load example
        </button>
      </div>
      <div class="d-flex justify-content-end mt-3">
        <button 
          type="submit" 
          class="btn btn-primary"
          :disabled="isLoading"
        >
          <span v-if="isLoading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
          <span v-else>Search</span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from '../utils/http'

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
    alert('Please enter gene IDs');
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
        alert('Error: ' + (responseData.error || 'Failed to get task ID'))
      }
  } catch (error) {
    console.error('Error submitting form:', error)
    alert('Error submitting form: ' + (error.message || 'Unknown error'))
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
  min-height: 120px;
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