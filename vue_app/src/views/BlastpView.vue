<script setup lang="ts">
import { ref, inject } from 'vue'
import { useRouter } from 'vue-router'

// 注入全局loading状态管理方法
const showLoading = inject('showLoading') as () => void
const hideLoading = inject('hideLoading') as () => void

const router = useRouter()
const sequence = ref('')
const evalue = ref(0.01)
const maxTargetSeqs = ref(30)
const error = ref('')

const exampleSequence = "MGEAIKKQEGVSTVKEDNKLIDSKKKKANNSNLAKKTSWRRIDLMATKNQRNDDSSTRKRKSSEGEFDMCGIEVAYEDELKRLKQEGKEDRDECKVKNPDKSLISAYIHDIQQLLVKYRKCRFEYIPPMENNLAHILATETLKNKKEFYLVGSVPKSAEKKEERDRVREPD"

const fillExample = () => {
  sequence.value = exampleSequence
}
console.log('exampleSequence:', exampleSequence);

const handleSubmit = async () => {
  if (!sequence.value.trim()) {
    error.value = 'Please enter a protein sequence'
    return
  }
  
  error.value = ''
  console.log('sequence.value:', sequence.value);
  
  // 显示全局加载状态
  showLoading()
  
  try {
    // 实现BLASTP API调用
    console.log('Submitting BLASTP search:', {
      sequence: sequence.value,
      evalue: evalue.value,
      maxTargetSeqs: maxTargetSeqs.value
    })
    
    // 创建FormData对象来发送表单数据
    const formData = new FormData()
    formData.append('sequence', sequence.value)
    formData.append('evalue', evalue.value.toString())
    formData.append('max_target_seqs', maxTargetSeqs.value.toString())
    
    // 构建完整的API URL
    const apiUrl = '/tools/blastp/api/blastp/'
    console.log('API URL:', apiUrl)
    
    // 添加详细的请求日志
    console.log('FormData entries:')
    for (const [key, value] of formData.entries()) {
      console.log(`${key}: ${value}`)
    }
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      body: formData,
      headers: {
        'Accept': 'application/json'
      }
    })
    
    // 添加响应日志
    console.log('Response status:', response.status)
    console.log('Response statusText:', response.statusText)
    console.log('Response headers:', Object.fromEntries(response.headers.entries()))
    
    // 检查响应是否成功
    if (!response.ok) {
      const errorText = await response.text()
      console.error('Response error text:', errorText)
      throw new Error(`HTTP error! status: ${response.status}, text: ${errorText}`)
    }
    
    const results = await response.json()
    
    // 将结果传递给结果页面
    router.push({
      name: 'blastpResults',
      query: {
        results: encodeURIComponent(JSON.stringify(results))
      }
    })
    
  } catch (err) {
    error.value = 'BLASTP search failed. Please try again. ' + (err as Error).message
    console.error('BLASTP error:', err)
    console.error('Error details:', JSON.stringify(err, Object.getOwnPropertyNames(err)))
  } finally {
    // 隐藏全局加载状态
    hideLoading()
  }
}

const handleReset = () => {
  sequence.value = ''
  evalue.value = 0.01
  maxTargetSeqs.value = 30
  error.value = ''
}
</script>

<template>
  <div class="container mt-4">
    <h2 class="mb-4">BLASTP</h2>
    
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    
    <div class="card">
      <div class="card-body">
        <form @submit.prevent="handleSubmit">
          
          <div class="form-group mb-3">
            <label for="sequence" class="form-label">Protein Sequence:</label>
            <textarea 
              class="form-control" 
              id="sequence" 
              v-model="sequence" 
              rows="10" 
              required
            ></textarea>
            <button 
              type="button" 
              class="btn btn-sm btn-outline-secondary mt-2" 
              @click="fillExample"
            >
              Load Example
            </button>
          </div>
          
          <div class="row mb-3">
            <div class="col-md-6">
              <div class="form-group">
                <label for="evalue" class="form-label">E-value threshold:</label>
                <input 
                  type="number" 
                  class="form-control" 
                  id="evalue" 
                  v-model.number="evalue" 
                  step="0.01" 
                  min="0"
                >
              </div>
            </div>
            <div class="col-md-6">
              <div class="form-group">
                <label for="max_target_seqs" class="form-label">Maximum target sequences:</label>
                <input 
                  type="number" 
                  class="form-control" 
                  id="max_target_seqs" 
                  v-model.number="maxTargetSeqs" 
                  min="1" 
                  max="50"
                >
              </div>
            </div>
          </div>
          
          <button type="submit" class="btn btn-primary me-2">
            <i class="fas fa-search"></i> Search
          </button>
          
          <button type="button" class="btn btn-outline-secondary" @click="handleReset">
            <i class="fas fa-undo"></i> Reset
          </button>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.form-control {
  border: 1px solid #ced4da;
  border-radius: 0.375rem;
}

.form-control:focus {
  border-color: #86b7fe;
  box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

.btn {
  border-radius: 0.375rem;
  padding: 0.375rem 0.75rem;
}

.btn-primary {
  background-color: #0d6efd;
  border-color: #0d6efd;
}

.btn-primary:hover {
  background-color: #0b5ed7;
  border-color: #0a58ca;
}

.btn-outline-secondary {
  color: #6c757d;
  border-color: #6c757d;
}

.btn-outline-secondary:hover {
  color: #fff;
  background-color: #6c757d;
  border-color: #6c757d;
}

.alert {
  border-radius: 0.375rem;
  padding: 0.75rem 1rem;
}

.alert-danger {
  color: #842029;
  background-color: #f8d7da;
  border-color: #f5c2c7;
}

.card {
  border: 1px solid rgba(0, 0, 0, 0.125);
  border-radius: 0.5rem;
  box-shadow: 0 0.125rem 0.25rem rgba(0, 0, 0, 0.075);
}

.card-body {
  padding: 1.5rem;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.mt-4 {
  margin-top: 1.5rem;
}

.mb-3 {
  margin-bottom: 1rem;
}

.mb-4 {
  margin-bottom: 1.5rem;
}

.me-2 {
  margin-right: 0.5rem;
}

.form-label {
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-group {
  margin-bottom: 1rem;
}
</style>