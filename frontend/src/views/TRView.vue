<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 宸︿晶杈规爮 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>Transcription Regulators factors<el-icon class="info-icon"><QuestionFilled /></el-icon></h3>
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

      <!-- 涓诲唴瀹瑰尯鍩?-->
      <div class="col-md-9">
        <div class="main-content">
          <h2>Annotated transcription regulators factors</h2>
          
          <!-- 杞綍鍥犲瓙瀹舵棌澶嶉€夋 -->
          <div class="tf-families mt-4">
            <div class="row">
              <div class="col-md-3" v-for="family in tfFamilies" :key="family.name">
                <el-checkbox v-model="family.checked" class="tf-checkbox" @change="handleFamilyChange">
                  {{ family.name }}({{ family.count }})
                </el-checkbox>
              </div>
            </div>
          </div>

          <!-- 琛ㄦ牸 -->
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
            
            <!-- 鍔犺浇鐘舵€?-->
            <el-skeleton v-if="loading" :rows="10" animated />
            
            <!-- 琛ㄦ牸鍐呭 -->
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

            <!-- 鍒嗛〉 -->
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
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import { useFamilyStore } from '@/stores/familyInfo'

export default {
  name: 'TRView',
  components: {
    Search
  },
  setup() {
    const { t } = useI18n()
    const { selectedGenome, genomeOptions, genomeLoading, cascaderProps, ensureGenomesLoaded, pickDefaultGenome, setSelectedGenome } = useGenomeSelector('G.anomalumB1_HAU_v1')
    const familyStore = useFamilyStore()
    
    const familyInfo = computed(() => familyStore.familyInfo)
    const familyList = computed(() => familyStore.familyList)
    
    const tfFamilies = computed(() => {
      return familyInfo.value.map((family, index) => ({
        name: family.name,
        count: family.count,
        checked: index === 0
      }))
    })
    
    const tfData = ref([])
    const searchQuery = ref('')
    const currentPage = ref(1)
    const pageSize = ref(10)
    const totalCount = ref(0)
    const loading = ref(false)
    const originalTFData = ref([])
    
    watch(familyList, (newList) => {
      if (newList && newList.length > 0) {
        originalTFData.value = newList
        console.log('Updated originalTFData from familyList:', originalTFData.value.length, 'items')
        if (selectedGenome.value.length > 0) {
          filterTFData()
        }
      }
    }, { immediate: true })
    
    const paginatedTFData = computed(() => {
      const startIndex = (currentPage.value - 1) * pageSize.value
      const endIndex = startIndex + pageSize.value
      return tfData.value.slice(startIndex, endIndex)
    })
    
    const fetchTFDataByGenome = async () => {
      if (selectedGenome.value.length === 0) {
        tfData.value = []
        totalCount.value = 0
        return
      }
      
      loading.value = true
      try {
        if (originalTFData.value.length > 0) {
          filterTFData()
        } else {
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
      
      let filteredData = originalTFData.value
      console.log('Filtered by genome:', filteredData.length, 'items')
      
      const selectedFamilies = tfFamilies.value.filter(f => f.checked).map(f => f.name)
      console.log('Selected families:', selectedFamilies)
      if (selectedFamilies.length > 0) {
        filteredData = filteredData.filter(item => selectedFamilies.includes(item.TF_name))
        console.log('Filtered by families:', filteredData.length, 'items')
      }
      
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filteredData = filteredData.filter(item => 
          item.TF_name.toLowerCase().includes(query) ||
          item.geneid.toLowerCase().includes(query)
        )
        console.log('Filtered by search:', filteredData.length, 'items')
      }
      
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
    
    const handleGenomeChange = async () => {
      currentPage.value = 1
      originalTFData.value = []
      tfData.value = []
      totalCount.value = 0
      const genome = selectedGenome.value[selectedGenome.value.length - 1]
      familyStore.selectedGenome = genome
      familyStore.selectedClass = 'TR'
      await familyStore.fetchFamilies()
      fetchTFDataByGenome()
    }
    
    const handleFamilyChange = () => {
      currentPage.value = 1
      filterTFData()
    }
    
    const handleSearch = () => {
      currentPage.value = 1
      filterTFData()
    }
    
    const handlePageChange = () => {
    }
    
    const handlePageSizeChange = () => {
      currentPage.value = 1
    }
    
    const handleRowClick = (row) => {
      console.log('Selected row:', row)
    }
    
    const handleGeneClick = (geneId) => {
      console.log('Gene link clicked:', geneId)
      router.push({
        name: 'idSearchResults',
        query: { db_id: geneId }
      })
    }
    
    watch(pageSize, () => {
      currentPage.value = 1
    })
    
    onMounted(async () => {
      await ensureGenomesLoaded()
      const targetGenome = pickDefaultGenome()
      if (targetGenome) {
        setSelectedGenome(targetGenome)
        handleGenomeChange()
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

/* 宸︿晶杈规爮鏍峰紡 */
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

/* 涓诲唴瀹瑰尯鍩熸牱寮?*/
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

/* 杞綍鍥犲瓙瀹舵棌鏍峰紡 */
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

/* 琛ㄦ牸鏍峰紡 */
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

/* 鍩哄洜閾炬帴鏍峰紡 */
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

/* 鍝嶅簲寮忚璁?*/
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
