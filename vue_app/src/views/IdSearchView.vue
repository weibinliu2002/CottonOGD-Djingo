<script>
import { onMounted, ref } from 'vue'
import httpInstance from '../utils/http'
import { v4 as uuidv4 } from 'uuid'

export default {
  name: 'IdSearchView',
  inject: ['showLoading', 'hideLoading'],
  data() {
    return {
      geneIds: '',
      fileName: '',
      errorMessage: '',
    }
  },
  methods: {
    loadExample() {
      // 加载示例基因ID数据
      this.geneIds = `Ghir_A01G000040.1\nGhir_A01G000060\nGhir_A01G000290.1\nGhir_A01G000120.2`
      this.errorMessage = ''
    },
    reset() {
      // 重置基因ID输入框
      this.geneIds = ''
      this.fileName = ''
      this.errorMessage = ''
      // 重置文件输入框
      const fileInput = document.getElementById('fileInput')
      if (fileInput) {
        fileInput.value = ''
      }
    },
    handleFileSelect(event) {
      const file = event.target.files[0]
      if (file) {
        // 读取文件内容以提取基因ID
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            // 读取文件内容作为文本
            const fileContent = e.target.result
            // 假设文件内容是换行分隔的基因ID列表
            // 我们只需要内容字符串，不需要直接传输文件
            this.geneIds = fileContent.trim()
            this.fileName = file.name
            console.log('已从文件中读取基因ID:', this.geneIds)
          } catch (error) {
            this.errorMessage = '文件读取失败: ' + error.message
            console.error('文件读取错误:', error)
          }
        }
        reader.onerror = () => {
          this.errorMessage = '文件读取错误'
          console.error('文件读取器错误')
        }
        reader.readAsText(file)
      } else {
        this.geneIds = ''
        this.fileName = ''
      }
      // 重置文件输入，允许再次选择相同文件
      event.target.value = ''
    },
    async handleSubmit() {
      this.errorMessage = ''
      this.showLoading()
      
      try {
        // 验证是否有基因ID输入
        if (!this.geneIds || !this.geneIds.trim()) {
          throw new Error('请输入或上传基因ID')
        }
        
        // 生成唯一的请求ID
        const requestId = uuidv4();
        console.log('Request ID:', requestId);
        
        // 准备表单数据 - 使用URL编码格式而非FormData，避免CSRF问题
        const formDataString = `gene_ids=${encodeURIComponent(this.geneIds)}&request_id=${encodeURIComponent(requestId)}`
        console.log('formDataString:', formDataString)
        
        // 使用正确的http实例发送请求
        const response = await httpInstance.post('/tools/id-search/api/id-search-form/', formDataString, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Request-ID': requestId
          }
        })
        
        // 安全检查响应数据 - httpInstance的响应拦截器已经返回response.data
        if (!response) {
          throw new Error('无效的响应数据')
        }
        
        const data = response
        
        if (data.status !== 'success') {
          throw new Error(data.error || '搜索失败')
        }
        
        // 安全检查查询ID
        if (!data.query_ids || !Array.isArray(data.query_ids)) {
          throw new Error('无效的查询ID数据')
        }
        
        // 根据基因ID数量决定跳转页面
        console.log('查询ID:', data.query_ids[0])
        console.log('查询ID数量:', data.query_ids.length)
        if (data.query_ids.length === 1) {
          // 单个基因ID，跳转到结果详情页
          this.$router.push({
            path: '/tools/id-search/results/',
            query: { 
              id: data.query_ids[0], 
              request_id: requestId
            }
           
          })
        } else if (data.query_ids.length > 1) {
          // 多个基因ID，跳转到汇总页，通过URL传递基因ID
          this.$router.push({
            path: '/tools/id-search/id-search-summary/',
            query: { 
              id: data.query_ids.join(','), 
              request_id: requestId
            }
          })
        } else {
          // 没有找到匹配的基因ID
          throw new Error('没有找到匹配的基因ID')
        }
      } catch (error) {
        // 添加更详细的错误日志
        console.error('搜索错误详情:', error);
        console.error('错误类型:', typeof error);
        console.error('错误堆栈:', error.stack);
        console.error('错误响应:', error.response);
        
        // 设置错误消息
        this.errorMessage = error.response?.data?.error || error.message || '未知搜索错误';
        console.error('搜索错误:', this.errorMessage)
      } finally {
        this.hideLoading()
      }
    }
  }
}
</script>
<template>
  <div class="container mt-4">
    <h1>Search by ID</h1>
    <div class="text-left">
      <div class="card-body">
        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <div class="mb-4">
              <label for="geneIdInput" class="form-label">Input Gene IDs</label>
              <textarea class="form-control" id="geneIdInput" rows="6" placeholder="" v-model="geneIds" ref="gene_ids"></textarea>
              <button type="button" class="btn btn-info mt-2 mr-3" @click="loadExample">load example</button>
              <button type="button" class="btn btn-secondary mt-2" @click="reset">Reset</button>
              <p class="text-muted mt-1">one gene ID per line</p>
            </div>
            <div class="mb-4">
              <label class="form-label">select file</label>
              <div class="input-group">
                <input type="file" class="form-control" id="fileInput" accept=".txt,.csv,.xls,.xlsx" @change="handleFileSelect">
                <span class="input-group-text">{{ fileName || '未选择文件' }}</span>
              </div>
              <p class="text-muted mt-1">support .txt or .csv file</p>
            </div>
            <div class="d-flex gap-2">
              <button type="submit" class="btn btn-primary">
                Search
              </button>
            </div>
          </div>
        </form>
        
        <!-- 错误提示 -->
        <div v-if="errorMessage" class="alert alert-danger mt-3">
          {{ errorMessage }}
        </div>
      </div>
    </div>
  </div>
</template>


