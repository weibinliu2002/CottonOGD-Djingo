<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧边栏 - 选择基因组 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>JBrowse Views <el-icon class="info-icon"><QuestionFilled /></el-icon></h3>
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><VideoPlay /></el-icon> Genome</h4>
            <el-cascader
              v-model="selectedGenome"
              :options="genomeOptions"
              :props="cascaderProps"
              placeholder="选择基因组"
              class="w-100 mt-2"
              @change="handleGenomeChange"
              :loading="genomeLoading"
            />
          </div>
        
            <div class="text-muted">Please select a genomic</div>
          
          <!-- 操作按钮 -->
          <div class="mt-4">
            
            <div class="d-grid gap-2">
              <button @click="refreshIframe" class="btn btn-secondary">
                Refresh View
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 主内容区域 - 展示JBrowse -->
      <div class="col-md-9">
        <div class="main-content">
          <h2>JBrowse 可视化</h2>
          <div v-if="selectedGenomeInfo" class="genome-info">
              <p><strong>Genome:</strong> {{ selectedGenomeInfo.name }}</p>
              <p><strong>Version:</strong> {{ selectedGenomeInfo.assembly }}</p>
            </div>
          <div class="embed-container">
            <iframe :key="iframeKey" :src="currentIframeUrl" width="100%" height="800px" frameborder="0"></iframe>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { QuestionFilled, VideoPlay } from '@element-plus/icons-vue'
import { useGenomeStore } from '@/stores/genome_info'

// 获取第一个染色体名称的函数
const getFirstChromosome = async (genomeName) => {
  try {
    const faiUrl = `/assets/jbrowse/data/${genomeName}/${genomeName}.genome.fa.gz.fai`
    console.log('尝试获取.fai文件:', faiUrl)
    const response = await fetch(faiUrl)
    
    if (!response.ok) {
      console.warn(`无法获取 .fai 文件: ${faiUrl}, 状态码: ${response.status}`)
      return 'Ghir_A01' // 默认 fallback
    }
    console.log('成功获取.fai文件响应')
    const text = await response.text()
    console.log('fai文件内容长度:', text.length)
    
    const lines = text.trim().split('\n')
    console.log('fai文件行数:', lines.length)
    
    if (lines.length === 0) {
      console.warn('.fai 文件为空')
      return 'Ghir_A01'
    }
    
    // 获取第一行的第一个字段（染色体名称）
    const firstChromosome = lines[0].split('\t')[0]
    
    console.log(`获取到的第一个染色体: ${firstChromosome}`)
    return firstChromosome
    
  } catch (error) {
    console.error('获取第一个染色体时出错:', error)
    return 'Ghir_A01' // 出错时返回默认值
  }
}

export default {
  name: 'JbrowseView',
  components: {
    QuestionFilled,
    VideoPlay
  },
  setup() {
    // 获取基因组store
    const genomeStore = useGenomeStore()
    
    // 选中的基因组（级联选择器使用数组格式）
    const selectedGenome = ref([]) 
    
    // 级联选择器配置
    const cascaderProps = ref({
      multiple: false,
      checkStrictly: false,
      expandTrigger: 'click',
      showAllLevels: false
    })
    
    // 从store获取基因组选项
    const genomeOptions = computed(() => genomeStore.genomeOptions)
    // 从store获取加载状态
    const genomeLoading = computed(() => genomeStore.loading)
    
    // 当前iframe URL
    const currentIframeUrl = ref('/assets/jbrowse/index.html?assembly=Ghirsutum_genome_HAU_v1.0&tracks=Ghirsutum_genome_HAU_v1.0.gff&loc=Ghir_A01:1-1000000')
    
    
    // iframe刷新key
    const iframeKey = ref(0)
    
    // 选中的基因组信息
    const selectedGenomeInfo = ref(null)
    
    // 处理基因组选择变化
    const handleGenomeChange = async (value) => {
      console.log('选择的基因组值:', value)
      
      if (value && value.length > 0) {
        // 查找选中的基因组数据，级联选择器返回的是数组，最后一个元素是选中的基因组名称
        const selectedValue = value[value.length - 1]
        
        // 简化处理，直接使用选中的值作为基因组名称
        const genomeName = selectedValue
        selectedGenomeInfo.value = {
          name: genomeName,
          assembly: genomeName
        }
        
        console.log('选择的基因组:', genomeName)
        
        // 获取第一个染色体名称
        const firstChromosome = await getFirstChromosome(genomeName)
        console.log('第一个染色体:', firstChromosome)
        
        // 使用name作为URL参数，因为目录名与name匹配
        const url = `/assets/jbrowse/index.html?config=data/${genomeName}/config.json&assembly=${genomeName}&tracks=GFF&loc=${firstChromosome}:1-1000000`
        console.log('构建的URL:', url)
        currentIframeUrl.value = url
        refreshIframe()
      }
    }
    
    // 刷新iframe
    const refreshIframe = () => {
      iframeKey.value++
    }
    
    // 从后端获取基因组数据
    const fetchGenomes = async () => {
      await genomeStore.fetchGenomes()
    }
    
    // 组件挂载时初始化
    onMounted(() => {
      fetchGenomes()
    })
    
    return {
      selectedGenome,
      genomeOptions,
      genomeLoading,
      cascaderProps,
      currentIframeUrl,
      iframeKey,
      selectedGenomeInfo,
      handleGenomeChange,
      refreshIframe
    }
  }
}
</script>

<style scoped>
.container-fluid {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

/* 左侧边栏样式 */
.sidebar {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  height: fit-content;
}

.sidebar h3 {
  font-size: 1.2rem;
  font-weight: bold;
  color: #333;
}

.info-icon {
  font-size: 1rem;
  margin-left: 5px;
  color: #409eff;
  cursor: pointer;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: bold;
  color: #333;
  margin-bottom: 0;
}

.play-icon {
  font-size: 0.8rem;
  margin-right: 5px;
  color: #e6a23c;
}

/* 基因组信息样式 */
.genome-info {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
  font-size: 0.9rem;
}

/* 主内容区域样式 */
.main-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.main-content h2 {
  font-size: 1.5rem;
  font-weight: bold;
  color: #333;
}

/* 嵌入容器样式 */
.embed-container {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  margin-top: 20px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container-fluid {
    padding: 10px;
  }
  
  .sidebar,
  .main-content {
    padding: 15px;
    margin-bottom: 20px;
  }
}
</style>
