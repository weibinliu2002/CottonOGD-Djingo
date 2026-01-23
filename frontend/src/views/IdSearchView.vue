<template>
  <div class="container mt-4">
    <h1>Search by ID</h1>
    <el-card class="mt-4">
      <el-form @submit.prevent="handleSubmit" label-width="120px">
        <el-form-item label="Input Gene IDs">
          <el-input
            type="textarea"
            :rows="6"
            placeholder="请输入基因ID，一行一个"
            v-model="gene_id"
            ref="gene_ids"
          />
          <div class="mt-2">
            <el-button type="info" @click="loadExample">load example</el-button>
            <el-button type="default" @click="reset" class="ml-2">Reset</el-button>
          </div>
          <div class="text-muted mt-1">one gene ID per line</div>
        </el-form-item>
        
        <el-form-item label="Select Genome">
          <el-tree-select
            v-model="genome_id"
            :data="genomeOptions"
            :props="{
              value: 'value',
              label: 'label',
              children: 'children'
            }"
            placeholder="Select Genome"
            style="width: 100%"
            :loading="loading"
            multiple
          />
        </el-form-item>
        
        <el-form-item label="select file">
          <el-upload
            class="upload-demo"
            action="#"
            :auto-upload="false"
            :on-change="handleFileSelect"
            :show-file-list="false"
            accept=".txt,.csv,.xls,.xlsx"
          >
            <template #default>
              <el-button type="primary">
                <el-icon><Upload /></el-icon>
                <span>选择文件</span>
              </el-button>
              <span class="ml-2">{{ fileName || '未选择文件' }}</span>
            </template>
          </el-upload>
          <div class="text-muted mt-1">support .txt or .csv file</div>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" native-type="submit">Search</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 错误提示 -->
      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        show-icon
        class="mt-3"
      />
    </el-card>
  </div>
</template>
<script>
import { onMounted, ref } from 'vue'
import httpInstance from '@/utils/http'
import { v4 as uuidv4 } from 'uuid'
import { useGenomeStore } from '@/stores/genome_info'
import { Upload } from '@element-plus/icons-vue'
export default {
  name: 'IdSearchView',
  inject: ['showLoading', 'hideLoading'],
  components: {
    Upload
  },
  data() {
    return {
      gene_id: '',
      genome_id: ['G.hirsutum(AD1)TM-1_HAU_v1.1'],
      fileName: '',
      errorMessage: '',
      genomeStore: useGenomeStore()
    }
  },
  computed: {
    genomeOptions() {
      return this.genomeStore.genomeOptions
    },
    loading() {
      return this.genomeStore.loading
    }
  },
  mounted() {
    // 加载基因组数据
    this.genomeStore.fetchGenomes()
  },
  methods: {
    loadExample() {
      // 加载示例基因ID数据
      this.gene_id = `Ghir_A01G000040.1\nGhir_A01G000060\nGhir_A01G000290.1\nGhir_A01G000120.2`
      this.errorMessage = ''
    },
    reset() {
      // 重置基因ID输入框
      this.gene_id = ''
      this.fileName = ''
      this.errorMessage = ''
    },
    handleFileSelect(file) {
      const selectedFile = file.raw
      if (selectedFile) {
        // 读取文件内容以提取基因ID
        const reader = new FileReader()
        reader.onload = (e) => {
          try {
            // 读取文件内容作为文本
            const fileContent = e.target.result
            // 假设文件内容是换行分隔的基因ID列表
            // 我们只需要内容字符串，不需要直接传输文件
            this.gene_id = fileContent.trim()
            this.fileName = selectedFile.name
            console.log('已从文件中读取基因ID:', this.gene_id)
          } catch (error) {
            this.errorMessage = '文件读取失败: ' + error.message
            console.error('文件读取错误:', error)
          }
        }
        reader.onerror = () => {
          this.errorMessage = '文件读取错误'
          console.error('文件读取器错误:', reader.error)
        }
        reader.readAsText(selectedFile)
      } else {
        this.gene_id = ''
        this.fileName = ''
      }
    },
    async handleSubmit() {
      this.errorMessage = ''
      this.showLoading()
      
      try {
        // 验证是否有基因ID输入
        if (!this.gene_id || !this.gene_id.trim()) {
          throw new Error('请输入或上传基因ID')
        }
        
        // 生成唯一的请求ID
        const requestId = uuidv4();
        console.log('uuid:', requestId);
        
        // 准备表单数据 - 使用URL编码格式而非FormData，避免CSRF问题
        // 对于多选基因组，将数组转换为逗号分隔的字符串
        const genomeIdString = Array.isArray(this.genome_id) ? this.genome_id.join(',') : this.genome_id
        const formDataString = `gene_id=${encodeURIComponent(this.gene_id)}&genome_id=${encodeURIComponent(genomeIdString)}&request_id=${encodeURIComponent(requestId)}`
        console.log('formDataString:', formDataString)
        
        // 先发送登录请求，确保 UUID 被正确注册
        await httpInstance.post('/CottonOGD_api/login/', {}, {
          headers: {
            'Content-Type': 'application/json',
            'uuid': requestId
          }
        })
        console.log('登录成功:', requestId)
        
        // 然后发送 geneid_summary 请求
        const response = await httpInstance.post('/CottonOGD_api/geneid_summary/', formDataString, {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-Request-ID': requestId,
            'uuid': requestId
          }
        })
        
        // 安全检查响应数据 - httpInstance的响应拦截器已经返回response.data
        if (!response) {
          throw new Error('无效的响应数据')
        }
        
        await httpInstance.post('/CottonOGD_api/logout/', {}, {
          headers: {
            'Content-Type': 'application/json',
            'uuid': requestId
          }
        })
        console.log('注销成功:', requestId)
        const data = response
        console.log('data:', data)
        
        // 解析 search_map，建立输入 ID 与 db_id 的关系
        
        const searchMap = JSON.parse(data.search_map)
        console.log('解析后的 search_map:', searchMap)
         
        // 解析基因注释结果
      
        const geneidResult = JSON.parse(data.geneid_result)
        console.log('解析后的 geneid_result:', geneidResult)
                
        // 解析基因信息结果
        const geneInfoResult = JSON.parse(data.gene_info_result)
        console.log('解析后的 gene_info_result:', geneInfoResult)
         
        
        // 构建查询ID列表（从 search_map 中提取 db_id）
        let query_ids = []
        if (searchMap && typeof searchMap === 'object') {
          for (const [inputId, info] of Object.entries(searchMap)) {
            if (info && info.db_id) {
              query_ids.push(info.db_id)
            }
          }
        }
        
        // 去重
        query_ids = [...new Set(query_ids)]
        console.log('构建的查询ID:', query_ids)
        
        // 安全检查查询ID
        if (!query_ids || !Array.isArray(query_ids)) {
          throw new Error('无效的查询ID数据')
        }
        // 根据基因ID数量决定跳转页面
        console.log('查询ID:', query_ids[0])
        console.log('查询ID数量:', query_ids.length)
        if (query_ids.length === 1) {
          // 单个基因ID，跳转到结果详情页
          this.$router.push({
            path: '/tools/id-search/results/',
            query: { 
              db_id: query_ids[0], 
              request_id: requestId
            }
          })
        } else if (query_ids.length > 1) {
          // 多个基因ID，跳转到汇总页，通过URL传递基因ID
          this.$router.push({
            path: '/tools/id-search/id-search-summary/',
            query: { 
              db_id: query_ids.join(','), 
              request_id: requestId,
              searchMap:JSON.stringify(searchMap),
              geneInfoResult:JSON.stringify(geneInfoResult),
              geneidResult:JSON.stringify(geneidResult),
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

