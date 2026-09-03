<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧栏：基因组选择（树形） -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>{{ t('transcription_factors_') }} <el-icon class="info-icon"><QuestionFilled /></el-icon></h3>
          <div class="mt-4">
            <h4 class="sidebar-title"><el-icon class="play-icon"><VideoPlay /></el-icon> {{ t('select_genome') }}</h4>
            <el-tree-v2
              ref="genomeTreeRef"
              :data="genomeOptions"
              :props="genomeTreeProps"
              node-key="value"
              :height="460"
              highlight-current
              :current-node-key="selectedGenomeName"
              :default-expanded-keys="defaultExpandedKeys"
              class="genome-tree w-100 mt-2"
              v-loading="genomeLoading"
              @node-click="handleGenomeNodeClick"
            />
          </div>
        </div>
      </div>

      <!-- 主内容区域 -->
      <div class="col-md-9">
        <div class="main-content">
          <h2>{{ t('annotated_transcription_factors') }}</h2>

          <!-- 转录因子家族：单选（选中后联动下方 列表 / 进化树） -->
          <div class="tf-families mt-4" v-loading="familyLoading">
            <el-radio-group v-model="selectedFamilyName" @change="handleFamilyChange">
              <div class="row">
                <div class="col-md-3" v-for="family in familyInfo" :key="family.name">
                  <el-radio :value="family.name" class="tf-radio">
                    {{ family.name }}({{ family.count }})
                  </el-radio>
                </div>
              </div>
            </el-radio-group>
          </div>

          <!-- 选中转录因子家族后：基因列表 / 系统发生树 -->
          <el-tabs v-if="selectedFamilyName" v-model="activeTab" type="border-card" class="tf-tabs mt-4">
            <el-tab-pane :label="t('gene_list')" name="family">
              <div class="tf-table mt-2">
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

                <template v-else>
                  <!-- 表格内容：复选框多选，选中基因在进化树中高亮 -->
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

                  <div v-if="highlightGenes.length" class="highlight-hint mt-3">
                    <el-icon><View /></el-icon>
                    {{ t('highlight_in_tree') }}: {{ highlightGenes.length }}
                  </div>
                </template>
              </div>
            </el-tab-pane>
            <el-tab-pane :label="t('phylotree')" name="phylotree">
              <PhyloTreeViewer
                v-if="selectedGenomeName"
                :key="treeKey"
                :genome="selectedGenomeName"
                category="TF"
                :family="selectedFamilyName"
                :highlight-genes="highlightGenes"
              />
              <el-empty v-else :description="t('select_genome_first')" />
            </el-tab-pane>
          </el-tabs>

          <!-- 未选择家族时的空状态 -->
          <el-empty v-else class="mt-4" :description="t('select_family_first')" />
        </div>
      </div>
    </div>

    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { QuestionFilled, VideoPlay, Search, View } from '@element-plus/icons-vue'
import PhyloTreeViewer from '@/components/data-display/PhyloTreeViewer.vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import router from '@/router'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { useFamilyStore } from '@/stores/modules/family'
import { useNavigationStore } from '@/stores/modules/navigation'

export default {
  name: 'TFView',
  components: {
    QuestionFilled,
    VideoPlay,
    Search,
    View,
    PhyloTreeViewer
  },
  setup() {
    const { t } = useI18n()
    const route = useRoute()
    // 基因组选择器（树形单选）
    const {
      selectedGenome,
      selectedGenomeName,
      genomeOptions,
      genomeLoading,
      allGenomes,
      ensureGenomesLoaded,
      pickDefaultGenome,
      setSelectedGenome
    } = useGenomeSelector()
    const navigationStore = useNavigationStore()
    const familyStore = useFamilyStore()

    // Tab 切换
    const activeTab = ref('family')
    const treeKey = ref(0)

    // el-tree-v2 配置：分组节点（基因组类别）可选展开，叶子节点（基因组）单选
    const genomeTreeRef = ref(null)
    const genomeTreeProps = { label: 'label', children: 'children', value: 'value' }
    const defaultExpandedKeys = computed(() => genomeOptions.value.map((g) => g.value))

    // 当前单选选中的转录因子家族
    const selectedFamilyName = ref('')
    // 表格中勾选、需要在进化树中高亮的基因 id 列表
    const highlightGenes = ref([])
    const tfTableRef = ref(null)

    // 从 store 获取家族信息 / 列表 / 加载状态
    const familyInfo = computed(() => familyStore.familyInfo)
    const familyList = computed(() => familyStore.familyList)
    const familyLoading = computed(() => familyStore.loading)

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

    // 监听 familyList 变化，更新 originalTFData，并默认选中第一个家族
    watch(familyList, (newList) => {
      if (newList && newList.length > 0) {
        originalTFData.value = newList
        // 单选：默认选中第一个家族（若当前未选或已失效）
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

    // 计算分页后的数据
    const paginatedTFData = computed(() => {
      const startIndex = (currentPage.value - 1) * pageSize.value
      const endIndex = startIndex + pageSize.value
      return tfData.value.slice(startIndex, endIndex)
    })

    // 根据选择的基因组获取转录因子数据
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

    // 清空表格选择（切换基因组 / 家族时调用，避免残留高亮）
    const clearTableSelection = () => {
      highlightGenes.value = []
      nextTick(() => {
        if (tfTableRef.value && typeof tfTableRef.value.clearSelection === 'function') {
          tfTableRef.value.clearSelection()
        }
      })
    }

    // 筛选转录因子数据
    const filterTFData = () => {
      if (originalTFData.value.length === 0 || selectedGenome.value.length === 0) {
        tfData.value = []
        totalCount.value = 0
        return
      }

      const genome = selectedGenome.value[selectedGenome.value.length - 1]

      // 先按基因组过滤
      let filteredData = originalTFData.value

      // 再按单选选中的家族过滤
      const familyName =
        selectedFamilyName.value || familyStore.familyInfo[0]?.name || ''
      if (familyName) {
        filteredData = filteredData.filter((item) => item.TF_name === familyName)
      }

      // 最后过滤搜索关键词
      if (searchQuery.value) {
        const query = searchQuery.value.toLowerCase()
        filteredData = filteredData.filter((item) =>
          (item.TF_name || '').toLowerCase().includes(query) ||
          (item.geneid || '').toLowerCase().includes(query)
        )
      }

      // 处理数据格式
      tfData.value = filteredData.map((item) => ({
        TF_name: item.TF_name || 'Unknown',
        TF_class: item.TF_class || 'Unknown',
        TF_gene: item.geneid || 'Unknown',
        db_id: item.id_id || 'Unknown',
        TF_genome: genome
      }))

      totalCount.value = tfData.value.length || 0
    }

    // el-tree-v2 节点点击：仅叶子节点（具体基因组）触发选择，分组节点仅展开/折叠
    const handleGenomeNodeClick = (data) => {
      if (!data) return
      if (data.children && data.children.length) return
      if (!data.value) return
      setSelectedGenome(data.value)
      handleGenomeChange()
    }

    // 处理基因组选择变化
    const handleGenomeChange = async () => {
      currentPage.value = 1
      // 清空所有本地数据
      originalTFData.value = []
      tfData.value = []
      totalCount.value = 0
      selectedFamilyName.value = ''
      clearTableSelection()
      // 更新 familyStore 中的 selectedGenome
      const genome = selectedGenome.value[selectedGenome.value.length - 1]
      familyStore.selectedGenome = genome
      familyStore.selectedClass = 'TF'
      // 强制进化树组件随新基因组重建
      treeKey.value += 1
      // 重新获取家族数据
      await familyStore.fetchFamilies()
      // 单选默认选中第一个家族
      selectedFamilyName.value = familyStore.familyInfo[0]?.name || ''
      fetchTFDataByGenome()
    }

    // 处理家族单选变化
    const handleFamilyChange = () => {
      currentPage.value = 1
      clearTableSelection()
      filterTFData()
    }

    // 表格多选变化：收集勾选基因，传给进化树高亮
    const handleSelectionChange = (rows) => {
      highlightGenes.value = (rows || []).map((r) => r.TF_gene).filter(Boolean)
    }

    // 处理搜索
    const handleSearch = () => {
      currentPage.value = 1
      filterTFData()
    }

    // 处理页码变化
    const handlePageChange = () => {
      // 页码变化时无需重新请求数据，仅更新计算属性
    }

    // 处理每页条数变化
    const handlePageSizeChange = () => {
      currentPage.value = 1
    }

    // 处理行点击
    const handleRowClick = (row) => {
      console.log('Selected row:', row)
    }

    // 处理基因链接点击
    const handleGeneClick = (geneId) => {
      console.log('Gene link clicked:', geneId)
      navigationStore.clearNavigationData('geneDetail')
      router.push({
        name: 'idSearchResults',
        query: { db_id: geneId }
      })
    }

    // 监听 pageSize 变化，确保 currentPage 被重置
    watch(pageSize, () => {
      currentPage.value = 1
    })

    // 组件挂载时加载数据
    onMounted(async () => {
      await ensureGenomesLoaded()
      // 优先使用 URL query 中的 genome 参数（从详情页快捷跳转过来）
      const queryGenome = typeof route.query.genome === 'string' ? route.query.genome : ''
      const targetGenome =
        queryGenome && allGenomes.value.includes(queryGenome) ? queryGenome : pickDefaultGenome()
      if (targetGenome) {
        setSelectedGenome(targetGenome)
        handleGenomeChange()
      }
    })

    return {
      t,
      activeTab,
      treeKey,
      // 基因组树
      genomeTreeRef,
      genomeTreeProps,
      defaultExpandedKeys,
      genomeOptions,
      genomeLoading,
      selectedGenome,
      selectedGenomeName,
      allGenomes,
      handleGenomeNodeClick,
      // 家族单选
      familyInfo,
      familyLoading,
      selectedFamilyName,
      handleFamilyChange,
      // 表格 / 高亮
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

/* 左侧栏样式 */
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

/* 基因组树样式 */
.genome-tree {
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 6px;
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

.tf-radio {
  display: block;
  margin-bottom: 8px;
  margin-right: 0;
  font-size: 0.9rem;
  white-space: normal;
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

/* 高亮提示 */
.highlight-hint {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #f56c6c;
  font-size: 0.9rem;
  font-weight: 600;
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
