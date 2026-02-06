<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧边栏 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>Transcription regulators <el-icon class="info-icon"><QuestionFilled /></el-icon></h3>
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><VideoPlay /></el-icon> {{ t('select_genome') }}</h4>
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
          <h2>Annotated transcription regulators</h2>
          
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
            <h4 class="table-title">{{ t('click_row_details') }}</h4>
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
                  placeholder="search"
                  prefix-icon="el-icon-search"
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
              <el-table-column prop="TF_name" :label="t('tf_name')" min-width="50" />
              <el-table-column prop="TF_class" :label="t('tf_class')" min-width="50" />
              <el-table-column prop="TF_gene" label="Gene" min-width="120">
                <template #default="scope">
                  <el-link type="primary" :underline="false" @click="handleGeneClick(scope.row.db_id)" class="gene-link">
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
import { useI18n } from 'vue-i18n'
import router from '@/router'
import httpInstance from '@/utils/http.js'
import { useGenomeStore } from '@/stores/genome_info'
import { useFamilyStore } from '@/stores/familyInfo'

export default {
  name: 'TRView',
  components: {
    //QuestionFilled,
    //VideoPlay,
    Search
  },
  setup() {
    const { t } = useI18n()
    // 获取基因组store
    const genomeStore = useGenomeStore()
    // 获取家族store
    const familyStore = useFamilyStore()
    
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
    
    // 从store获取家族信息
    const familyInfo = computed(() => familyStore.familyInfo)
    // 从store获取家族列表
    const familyList = computed(() => familyStore.familyList)
    // 从store获取家族加载状态
    const familyLoading = computed(() => familyStore.loading)
    
    // 从后端获取基因组数据
    const fetchGenomes = async () => {
      await genomeStore.fetchGenomes()
    }
    
    // 转录因子家族数据（带选中状态）
    const tfFamilies = computed(() => {
      return familyInfo.value.map((family, index) => ({
        name: family.name,
        count: family.count,
        checked: index === 0 // 默认选中第一个家族
      }))
    })
    
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
    
    // 原始转录因子数据（用于筛选）
    const originalTFData = ref([])
    
    // 监听 familyList 变化，更新 originalTFData
    watch(familyList, (newList) => {
      if (newList && newList.length > 0) {
        originalTFData.value = newList
        console.log('Updated originalTFData from familyList:', originalTFData.value.length, 'items')
        // 如果已经选择了基因组，重新过滤数据
        if (selectedGenome.value.length > 0) {
          filterTFData()
        }
      }
    }, { immediate: true })
    
    // 计算分页后的数据
    const paginatedTFData = computed(() => {
      const startIndex = (currentPage.value - 1) * pageSize.value
      const endIndex = startIndex + pageSize.value
      return tfData.value.slice(startIndex, endIndex)
    })
    
    // 获取家族数据
    const fetchFamilies = async () => {
      await familyStore.fetchFamilies()
    }
    
    // 根据选择的基因组获取转录因子数据
    const fetchTFDataByGenome = async () => {
      if (selectedGenome.value.length === 0) {
        tfData.value = []
        totalCount.value = 0
        return
      }
      
      loading.value = true
      try {
        // 直接使用存储的原始数据，根据基因组进行筛选
        if (originalTFData.value.length > 0) {
          // 调用筛选函数处理显示数据
          filterTFData()
        } else {
          // 如果没有原始数据，显示空
          tfData.value = []
          totalCount.value = 0
        }
      } catch (error) {
        console.error('Error processing TF data:', error)
        tfData.value = []
        totalCount.value = 0
      } finally {
        loading.value = false
      }
    }
    
    // 筛选转录因子数据
    const filterTFData = () => {
      console.log('Filtering TF data...')
      console.log('TF families:', tfFamilies.value)
      
      if (originalTFData.value.length === 0 || selectedGenome.value.length === 0) {
        console.log('No data or genome selected')
        tfData.value = []
        totalCount.value = 0
        return
      }
      
      const genome = selectedGenome.value[selectedGenome.value.length - 1]
      console.log('Current genome:', genome)
      
      // 先过滤基因组
      let filteredData = originalTFData.value//.filter(item => 
        //item.genome === genome || item.genome_id === genome
      //)
      console.log('Filtered by genome:', filteredData.length, 'items')
      
      // 再过滤家族
      const selectedFamilies = tfFamilies.value.filter(f => f.checked).map(f => f.name)
      console.log('Selected families:', selectedFamilies)
      if (selectedFamilies.length > 0) {
        filteredData = filteredData.filter(item => selectedFamilies.includes(item.TF_name))
        console.log('Filtered by families:', filteredData.length, 'items')
      }
      
      // 最后过滤搜索关键词
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filteredData = filteredData.filter(item => 
          item.TF_name.toLowerCase().includes(query) ||
          item.geneid.toLowerCase().includes(query)
        )
        console.log('Filtered by search:', filteredData.length, 'items')
      }
      
      // 处理数据格式
      tfData.value = filteredData.map(item => ({
        TF_name: item.TF_name || 'Unknown',
        TF_class: item.TF_class || 'Unknown',
        TF_gene: item.geneid || 'Unknown',
        db_id: item.id_id || 'Unknown',
        TF_genome: genome
      }))
      
      totalCount.value = tfData.value.length || 0
      console.log('Filtered TF data:', tfData.value)
    }
    
    // 处理基因组选择变化
    const handleGenomeChange = () => {
      currentPage.value = 1 // 重置页码
      fetchTFDataByGenome() // 仅在基因组改变时重新获取数据
    }
    
    // 处理家族选择变化
    const handleFamilyChange = () => {
      currentPage.value = 1 // 重置页码
      // 家族变化时调用筛选函数
      filterTFData()
    }
    
    // 处理搜索
    const handleSearch = () => {
      currentPage.value = 1 // 重置页码
      // 搜索变化时调用筛选函数
      filterTFData()
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
    const handleGeneClick = (row) => {
      console.log('Gene link clicked:', row)
      // 导航到ID搜索结果页面，并将基因ID作为参数传递
      router.push({
        name: 'idSearchResults',
        query: { db_id: row.db_id }
      })
    }
    
    // 监听pageSize变化，确保currentPage被重置
    watch(pageSize, () => {
      currentPage.value = 1
    })
    
    // 组件挂载时加载数据
    onMounted(async () => {
      await fetchGenomes() // 获取基因组列表
      await fetchFamilies() // 获取家族列表
      
      // 自动选择第一个基因组
      if (genomeOptions.value && genomeOptions.value.length > 0) {
        const firstGenome = genomeOptions.value[0]
        selectedGenome.value = [firstGenome.value]
        console.log('Auto-selected first genome:', firstGenome.label)
      }
    })
    
    return {
      t,
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
  color: #3a6ea5;
}

.info-icon {
  font-size: 1.2rem;
  margin-left: 5px;
  color: #3a6ea5;
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
  color: #3a6ea5;
  margin-bottom: 20px;
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