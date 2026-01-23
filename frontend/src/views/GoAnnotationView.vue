<template>
  <div class="container mt-4">
    <h2 class="mb-4">GO注释</h2>
    
    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>GO注释分析</span>
        </div>
      </template>
      
      <el-form @submit.prevent="handleSubmit" label-width="250px">
        <el-form-item label="输入基因列表 (每行一个基因或空格分隔)">
          <el-input
            type="textarea"
            :rows="10"
            v-model="geneList"
            placeholder="请输入基因列表"
          />
          <div class="mt-2">
            <el-button type="info" size="small" @click="fillExample">
              load example
            </el-button>
          </div>
        </el-form-item>
        
        <el-form-item label="每页显示结果数">
          <el-select
            v-model="perPage"
            placeholder="每页结果数"
            style="width: 120px"
          >
            <el-option value="5" label="5" />
            <el-option value="10" label="10" />
            <el-option value="25" label="25" />
            <el-option value="50" label="50" />
          </el-select>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" native-type="submit">
            <el-icon><Search /></el-icon>
            提交分析
          </el-button>
        </el-form-item>
        
        <el-form-item>
          <el-alert
            v-if="error"
            type="error"
            :title="error"
            show-icon
          />
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'

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
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
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

.card-header {
  font-size: 16px;
  font-weight: 500;
}
</style>