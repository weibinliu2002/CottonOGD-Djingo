<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧栏：基因组选择 + 转录调控因子家族选择 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>{{ t('transcription_regulators_factors') }} <el-icon class="info-icon"><QuestionFilled /></el-icon></h3>

          <!-- 基因组选择 -->
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><VideoPlay /></el-icon> {{ t('select_genome') }}</h4>
            <el-tree-v2
              ref="genomeTreeRef"
              :data="genomeOptions"
              :props="genomeTreeProps"
              node-key="value"
              :height="240"
              highlight-current
              :current-node-key="selectedGenomeName"
              :default-expanded-keys="defaultExpandedKeys"
              class="genome-tree w-100 mt-2"
              v-loading="genomeLoading"
              @node-click="handleGenomeNodeClick"
            />
          </div>

          <!-- 转录调控因子家族：树形单选（与基因组选择同样的滚动框样式） -->
          <div class="mt-4" v-loading="familyLoading">
            <h4 class="sidebar-title">{{ t('family_list') }}</h4>
            <el-tree-v2
              ref="familyTreeRef"
              :data="familyTreeData"
              :props="familyTreeProps"
              node-key="value"
              :height="300"
              highlight-current
              show-checkbox
              check-strictly
              :current-node-key="selectedFamilyName"
              :default-checked-keys="defaultCheckedFamilies"
              class="genome-tree w-100 mt-2"
              @check="handleFamilyCheck"
              @node-click="handleFamilyNodeClick"
            />
          </div>
        </div>
      </div>

      <!-- 右侧主内容：上方进化树，下方基因列表 -->
      <div class="col-md-9">
        <!-- 上方：系统发生树 -->
        <div class="main-content tree-panel">
          <h2>{{ t('phylotree') }}</h2>
          <PhyloTreeViewer
            v-if="selectedGenomeName && selectedFamilyName"
            :key="treeKey"
            :genome="selectedGenomeName"
            category="TR"
            :family="selectedFamilyName"
            :highlight-genes="highlightGenes"
          />
          <el-empty v-else-if="!selectedGenomeName" :description="t('select_genome_first')" />
          <el-empty v-else :description="t('select_family_first')" />
        </div>

        <!-- 下方：基因列表 -->
        <div class="main-content mt-3" v-if="selectedFamilyName">
          <h2>{{ t('gene_list') }}</h2>
          <div class="tf-table mt-2">
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

            <el-skeleton v-if="loading" :rows="5" animated />

            <template v-else>
              <el-table
                ref="tfTableRef"
                :data="paginatedTFData"
                style="width: 100%"
                row-key="TF_gene"
                @row-click="handleRowClick"
                @selection-change="handleSelectionChange"
                stripe
                border
              >
                <el-table-column type="selection" width="48" reserve-selection />
                <el-table-column prop="TF_name" :label="t('tf_name')" min-width="50" />
                <el-table-column prop="TF_class" :label="t('tf_class')" min-width="50" />
                <el-table-column prop="TF_gene" :label="t('gene')" min-width="120">
                  <template #default="scope">
                    <el-link type="primary" :underline="false" @click.stop="handleGeneClick(scope.row.db_id)" class="gene-link">
                      {{ scope.row.TF_gene }}
                    </el-link>
                  </template>
                </el-table-column>
                <el-table-column prop="TF_genome" :label="t('genome')" min-width="120" />
              </el-table>

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

              <div v-if="highlightGenes.length" class="highlight-hint mt-3">
                <el-icon><View /></el-icon>
                {{ t('highlight_in_tree') }}: {{ highlightGenes.length }}
              </div>
            </template>
          </div>
        </div>
      </div>
    </div>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { QuestionFilled, VideoPlay, Search, View } from '@element-plus/icons-vue'
import PhyloTreeViewer from '@/components/data-display/PhyloTreeViewer.vue'
import { useI18n } from 'vue-i18n'
import router from '@/router'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { useFamilyStore } from '@/stores/modules/family'

export default {
  name: 'TRView',
  components: {
    QuestionFilled,
    VideoPlay,
    Search,
    View,
    PhyloTreeViewer
  },
  setup() {
    const { t } = useI18n()
    const {
      selectedGenome,
      selectedGenomeName,
      genomeOptions,
      genomeLoading,
      allGenomes,
      ensureGenomesLoaded,
      pickDefaultGenome,
      setSelectedGenome
    } = useGenomeSelector('G.anomalumB1_HAU_v1')
    const familyStore = useFamilyStore()

    const treeKey = ref(0)

    // el-tree-v2 配置
    const genomeTreeRef = ref(null)
    const genomeTreeProps = { label: 'label', children: 'children', value: 'value' }
    const defaultExpandedKeys = ref([])

    // 转录调控因子家族树
    const familyTreeProps = { label: 'label', value: 'value' }
    const familyTreeRef = ref(null)
    const familyTreeData = computed(() =>
      familyStore.familyInfo.map((f) => ({
        value: f.name,
        label: `${f.name} (${f.count})`
      }))
    )

    const selectedFamilyName = ref('')
    const defaultCheckedFamilies = computed(() =>
      selectedFamilyName.value ? [selectedFamilyName.value] : []
    )

    const highlightGenes = ref([])
    const tfTableRef = ref(null)

    const familyInfo = computed(() => familyStore.familyInfo)
    const familyList = computed(() => familyStore.familyList)
    const familyLoading = computed(() => familyStore.loading)

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
        if (
          !selectedFamilyName.value ||
          !familyStore.familyInfo.some((f) => f.name === selectedFamilyName.value)
        ) {
          selectedFamilyName.value = familyStore.familyInfo[0]?.name || ''
        }
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
        console.error('Error processing TR data:', error)
        tfData.value = []
        totalCount.value = 0
      } finally {
        loading.value = false
      }
    }

    const clearTableSelection = () => {
      highlightGenes.value = []
      nextTick(() => {
        if (tfTableRef.value && typeof tfTableRef.value.clearSelection === 'function') {
          tfTableRef.value.clearSelection()
        }
      })
    }

    const filterTFData = () => {
      if (originalTFData.value.length === 0 || selectedGenome.value.length === 0) {
        tfData.value = []
        totalCount.value = 0
        return
      }
      const genome = selectedGenome.value[selectedGenome.value.length - 1]
      let filteredData = originalTFData.value
      const familyName = selectedFamilyName.value || familyStore.familyInfo[0]?.name || ''
      if (familyName) {
        filteredData = filteredData.filter((item) => item.TF_name === familyName)
      }
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filteredData = filteredData.filter((item) =>
          (item.TF_name || '').toLowerCase().includes(query) ||
          (item.geneid || '').toLowerCase().includes(query)
        )
      }
      tfData.value = filteredData.map((item) => ({
        TF_name: item.TF_name || 'Unknown',
        TF_class: item.TF_class || 'Unknown',
        TF_gene: item.geneid || 'Unknown',
        db_id: item.id_id || 'Unknown',
        TF_genome: genome
      }))
      totalCount.value = tfData.value.length || 0
    }

    const handleGenomeNodeClick = (data) => {
      if (!data) return
      if (data.children && data.children.length) return
      if (!data.value) return
      setSelectedGenome(data.value)
      handleGenomeChange()
    }

    const handleGenomeChange = async () => {
      currentPage.value = 1
      originalTFData.value = []
      tfData.value = []
      totalCount.value = 0
      selectedFamilyName.value = ''
      clearTableSelection()
      const genome = selectedGenome.value[selectedGenome.value.length - 1]
      familyStore.selectedGenome = genome
      familyStore.selectedClass = 'TR'
      treeKey.value += 1
      await familyStore.fetchFamilies()
      selectedFamilyName.value = familyStore.familyInfo[0]?.name || ''
      fetchTFDataByGenome()
    }

    const handleFamilyChange = () => {
      currentPage.value = 1
      clearTableSelection()
      filterTFData()
    }

    const handleFamilyNodeClick = (data) => {
      if (!data || !data.value) return
      selectedFamilyName.value = data.value
      if (familyTreeRef.value && typeof familyTreeRef.value.setCheckedKeys === 'function') {
        familyTreeRef.value.setCheckedKeys([data.value])
      }
      handleFamilyChange()
    }

    const handleFamilyCheck = (data, checkedInfo) => {
      const checkedKeys = checkedInfo && checkedInfo.checkedKeys ? checkedInfo.checkedKeys : []
      if (checkedKeys.length > 1) {
        const latest = checkedKeys[checkedKeys.length - 1]
        if (familyTreeRef.value && typeof familyTreeRef.value.setCheckedKeys === 'function') {
          familyTreeRef.value.setCheckedKeys([latest])
        }
        selectedFamilyName.value = latest
      } else if (checkedKeys.length === 1) {
        selectedFamilyName.value = checkedKeys[0]
      } else {
        if (selectedFamilyName.value) {
          if (familyTreeRef.value && typeof familyTreeRef.value.setCheckedKeys === 'function') {
            familyTreeRef.value.setCheckedKeys([selectedFamilyName.value])
          }
          return
        }
      }
      handleFamilyChange()
    }

    const handleSelectionChange = (rows) => {
      highlightGenes.value = (rows || []).map((r) => r.TF_gene).filter(Boolean)
    }

    const handleSearch = () => {
      currentPage.value = 1
      filterTFData()
    }

    const handlePageChange = () => {}

    const handlePageSizeChange = () => {
      currentPage.value = 1
    }

    const handleRowClick = (row) => {
      console.log('Selected row:', row)
    }

    const handleGeneClick = (geneId) => {
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
      treeKey,
      genomeTreeRef,
      genomeTreeProps,
      defaultExpandedKeys,
      genomeOptions,
      genomeLoading,
      selectedGenome,
      selectedGenomeName,
      allGenomes,
      handleGenomeNodeClick,
      familyTreeRef,
      familyTreeData,
      familyTreeProps,
      defaultCheckedFamilies,
      familyLoading,
      selectedFamilyName,
      handleFamilyNodeClick,
      handleFamilyCheck,
      tfTableRef,
      highlightGenes,
      handleSelectionChange,
      searchQuery,
      currentPage,
      pageSize,
      totalCount,
      tfData,
      paginatedTFData,
      loading,
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

.genome-tree {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 6px;
}

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

.tf-table {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
}

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

.highlight-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 0.9rem;
  font-weight: 600;
}

@media (max-width: 768px) {
  .container-fluid {
    padding: 10px;
  }
  .sidebar,
  .main-content {
    padding: 15px;
  }
}
</style>
