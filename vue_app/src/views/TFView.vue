<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧边栏 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>Transcription factors <el-icon class="info-icon"><QuestionFilled /></el-icon></h3>
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><VideoPlay /></el-icon> Select a genome</h4>
            <el-cascader
              v-model="selectedGenome"
              :options="genomeOptions"
              :props="cascaderProps"
              placeholder="Select genome"
              class="w-100 mt-2"
              @change="handleGenomeChange"
              :loading="genomeLoading"
            />
          </div>
        </div>
      </div>

      <!-- 主内容区域 -->
      <div class="col-md-9">
        <div class="main-content">
          <h2>Annotated transcription factors</h2>
          
          <!-- 转录因子家族复选框 -->
          <div class="tf-families mt-4">
            <div class="row">
              <div class="col-md-3" v-for="family in tfFamilies" :key="family.name">
                <el-checkbox v-model="family.checked" class="tf-checkbox" @change="handleFamilyChange">
                  {{ family.name }}({{ family.count }})
                </el-checkbox>
              </div>
            </div>
          </div>

          <!-- 表格 -->
          <div class="tf-table mt-4">
            <h4 class="table-title">Click on a row to check the details of the selected gene</h4>
            <div class="d-flex justify-content-between align-items-center mb-3">
              <div class="table-pagination">
                <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                layout="sizes"
                :total="totalCount"
                @current-change="handlePageChange"
                @update:page-size="handlePageSizeChange"
              />
              
              </div>
              <div class="table-search">
                <el-input
                  v-model="searchQuery"
                  placeholder="Search"
                  prefix-icon="Search"
                  size="small"
                  class="w-100"
                  @input="handleSearch"
                  clearable
                />
              </div>
            </div>
            
            <!-- 加载状态 -->
            <el-skeleton v-if="loading" :rows="10" animated />
            
            <!-- 表格内容 -->
            <el-table
              v-else
              :data="paginatedTFData"
              style="width: 100%"
              @row-click="handleRowClick"
              stripe
              border
            >
              <el-table-column prop="TF_name" label="TF Name" min-width="50" />
              <el-table-column prop="TF_class" label="TF Class" min-width="50" />
              <el-table-column prop="TF_gene" label="Gene" min-width="120">
                <template #default="scope">
                  <el-link type="primary" :underline="false" @click="handleGeneClick(scope.row.TF_gene)" class="gene-link">
                    {{ scope.row.TF_gene }}
                  </el-link>
                </template>
              </el-table-column>
              <el-table-column prop="TF_genome" label="Genome" min-width="120" />
            </el-table>

            <!-- 分页 -->
            <div class="d-flex justify-content-between align-items-center mt-3">
              <span class="table-info">
                Showing {{ (currentPage - 1) * pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalCount) }} of {{ totalCount }} entries
              </span>
               <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                layout="total, sizes, prev, pager, next, jumper"
                :total="totalCount"
                @current-change="handlePageChange"
                @update:page-size="handlePageSizeChange"
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue'
import { QuestionFilled, VideoPlay, Search } from '@element-plus/icons-vue'
import router from '@/router'

export default {
  name: 'TFView',
  components: {
    QuestionFilled,
    VideoPlay,
    Search
  },
  setup() {
    // 选中的基因组（级联选择器使用数组格式）
    const selectedGenome = ref([])
    
    // 级联选择器配置
    const cascaderProps = ref({
      multiple: false,
      checkStrictly: false,
      expandTrigger: 'click',
      showAllLevels: false
    })
    
    // 基因组级联选择器选项（从后端获取）
    const genomeOptions = ref([])
    
    // 基因组加载状态
    const genomeLoading = ref(false)
    
    // 从后端获取基因组数据
    const fetchGenomes = async () => {
      genomeLoading.value = true
      try {
        const response = await fetch('/Browse/api/species/')
        const data = await response.json()
        
        if (data.status === 'success') {
          // 处理后端返回的species数据，构建级联选择器所需的格式
          const speciesData = data.data
          console.log('speciesData:', speciesData)
          const genomes = {}  // 按Genome_type分组
          
          // 按Genome_type分组
          speciesData.forEach(species => {
            const genomeType = species.Genome_type || 'undefined'
            if (!genomes[genomeType]) {
              genomes[genomeType] = []
            }
            genomes[genomeType].push({
              value: species.name || species.Cotton_Species,
              label: species.name || species.Cotton_Species
            })
          })
          console.log('genomes:', genomes)
          // 转换为级联选择器格式
          genomeOptions.value = Object.entries(genomes).map(([type, items]) => ({
            value: type,
            label: type,
            children: items
          }))
        }
      } catch (error) {
        console.error('Error fetching genomes:', error)
      } finally {
        genomeLoading.value = false
      }
    }
    
    // 转录因子家族数据
    const tfFamilies = ref([])
    
    // 转录因子数据
    const tfData = ref([])
    
    // 搜索查询
    const searchQuery = ref('')
    
    // 分页相关
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalCount = ref(0)
    
    // 加载状态
    const loading = ref(false)
    
    // 计算分页后的数据
    const paginatedTFData = computed(() => {
      const startIndex = (currentPage.value - 1) * pageSize.value
      const endIndex = startIndex + pageSize.value
      return tfData.value.slice(startIndex, endIndex)
    })
    
    // 获取转录因子家族数据
    const fetchTFFamilies = async () => {
      try {
        const response = await fetch('/Browse/api/tf/families/')
        const data = await response.json()
        if (data.status === 'success') {
          // 将API返回的数据转换为复选框需要的格式
          tfFamilies.value = data.data.map((family, index) => ({
            name: family.name,
            count: family.count,
            checked: index === 0 // 默认选中第一个家族
          }))
          // 获取家族数据后重新加载转录因子数据
          fetchTFData()
        }
      } catch (error) {
        console.error('Error fetching TF families:', error)
      }
    }
    
    // 获取转录因子数据
    const fetchTFData = async () => {
      loading.value = true
      try {
        // 构建查询参数
        const params = new URLSearchParams()
        
        // 添加基因组过滤条件
        if (selectedGenome.value.length > 0) {
          params.append('genome', selectedGenome.value[selectedGenome.value.length - 1])
        }
        
        // 添加家族过滤条件
        const selectedFamilies = tfFamilies.value.filter(f => f.checked).map(f => f.name)
        if (selectedFamilies.length > 0) {
          params.append('family', selectedFamilies.join(','))
        }
        
        // 添加搜索关键词
        if (searchQuery.value) {
          params.append('search', searchQuery.value)
        }
        
        // 发送请求
        const response = await fetch(`/Browse/api/tf/?${params}`)
        const data = await response.json()
        
        if (data.status === 'success') {
          tfData.value = data.data
          totalCount.value = data.total || 0
        }
      } catch (error) {
        console.error('Error fetching TF data:', error)
      } finally {
        loading.value = false
      }
    }
    
    // 处理基因组选择变化
    const handleGenomeChange = () => {
      currentPage.value = 1 // 重置页码
      fetchTFData()
    }
    
    // 处理家族选择变化
    const handleFamilyChange = () => {
      currentPage.value = 1 // 重置页码
      fetchTFData()
    }
    
    // 处理搜索
    const handleSearch = () => {
      currentPage.value = 1 // 重置页码
      fetchTFData()
    }
    
    // 处理页码变化
    const handlePageChange = () => {
      // 页码变化时不需要重新请求数据，只需要更新计算属性
    }
    
    // 处理每页条数变化
    const handlePageSizeChange = () => {
      currentPage.value = 1 // 重置页码
      // 每页条数变化时不需要重新请求数据，只需要更新计算属性
    }
    
    // 处理行点击
    const handleRowClick = (row) => {
      console.log('Selected row:', row)
      // 这里可以添加点击行后的处理逻辑，比如跳转到详情页
    }
    
    // 处理基因链接点击
    const handleGeneClick = (geneId) => {
      console.log('Gene link clicked:', geneId)
      // 导航到ID搜索结果页面，并将基因ID作为参数传递
      router.push({
        name: 'idSearchResults',
        query: { id: geneId }
      })
    }
    
    // 监听pageSize变化，确保currentPage被重置
    watch(pageSize, () => {
      currentPage.value = 1
    })
    
    // 组件挂载时加载数据
    onMounted(() => {
      fetchGenomes()
      fetchTFFamilies()
      // fetchTFData()会在fetchTFFamilies获取到家族数据后自动调用，确保初始加载时应用家族过滤条件
    })
    
    return {
      selectedGenome,
      genomeOptions,
      genomeLoading,
      cascaderProps,
      tfFamilies,
      searchQuery,
      currentPage,
      pageSize,
      totalCount,
      tfData,
      paginatedTFData,
      loading,
      handleGenomeChange,
      handleFamilyChange,
      handleSearch,
      handlePageChange,
      handlePageSizeChange,
      handleRowClick,
      handleGeneClick
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

/* 转录因子家族样式 */
.tf-families {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
}

.tf-checkbox {
  display: block;
  margin-bottom: 8px;
  font-size: 0.9rem;
}

/* 表格样式 */
.table-title {
  color: #e6a23c;
  font-weight: bold;
  margin-bottom: 15px;
}

.tf-table {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
}

/* 基因链接样式 */
.gene-link {
  color: #409eff;
  text-decoration: none;
  cursor: pointer;
}

.gene-link:hover {
  color: #66b1ff;
  text-decoration: underline;
}

.table-pagination {
  display: flex;
  align-items: center;
}

.table-info {
  font-size: 0.9rem;
  color: #666;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container-fluid {
    padding: 10px;
  }
  
  .sidebar,
  .main-content {
    padding: 15px;
  }
  
  .tf-families .col-md-3 {
    width: 50%;
  }
}
</style>