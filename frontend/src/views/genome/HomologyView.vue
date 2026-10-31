<script setup lang="ts">
/**
 * 同源分析浏览页（阶段 3.3）
 *
 * 对标 SoyOmics 的 Homology 模块：orthogroup 列表 + 明细抽屉 + 单拷贝基因。
 *
 * 数据来源（重要）：
 * 后端目前**没有** orthogroup 相关接口（OrthoFinder 在 WorkFile/config.yaml 中
 * enabled: false，仓库内也无产物文件），因此统一走 src/api/index.ts 的 mock 分支。
 * 请求函数已写进统一 api 文件并预留 MOCK_FLAGS.orthogroups 开关，
 * 后端接口就绪后将该开关置 false 即可切到真实接口，本页无需改动。
 *
 * 交互：
 * - 关键词筛选：og_id / 功能注释模糊匹配
 * - 「仅单拷贝」开关：只看各物种恰好一个基因的 orthogroup
 * - 列排序：物种数 / 基因数 / og_id
 * - 分页 + 导出
 * - 点击行 → 抽屉展示该 orthogroup 的物种与基因明细
 */
import { ref, computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'
import {
  getOrthogroups,
  getOrthogroupDetail,
  getSingleCopyGenes,
  type OrthogroupItem,
  type OrthogroupDetail,
  type SingleCopyGene,
} from '@/api/index'

const { t } = useI18n()

// ============ 列表状态 ============
const loading = ref(false)
const errorText = ref('')
/** 后端返回的当前页数据 + 总数 */
const rows = ref<OrthogroupItem[]>([])
const serverTotal = ref(0)

/** 关键词（受控，交给增强表格统一管理筛选体验） */
const keyword = ref('')
const singleCopyOnly = ref(false)

// ============ 增强表格（排序 + 分页 + 导出） ============
type Row = OrthogroupItem

const table = useEnhancedTable<Row>(rows, {
  pageSize: 10,
  pageSizes: [10, 20, 50, 100],
  // 关键词已在服务端/ mock 层过滤，这里不重复按字段过滤
  searchFields: [],
})

/** 导出列定义 */
const exportColumns: ExportColumn<Row>[] = [
  { key: 'og_id', label: 'Orthogroup ID' },
  { key: 'species_count', label: 'Species Count' },
  { key: 'gene_count', label: 'Gene Count' },
  { key: 'is_single_copy', label: 'Single Copy', formatter: (row) => (row.is_single_copy ? 'Yes' : 'No') },
  { key: 'annotation', label: 'Annotation', formatter: (row) => row.annotation ?? '-' },
]

// ============ 取数 ============
/** 拉取列表：关键词 / 单拷贝开关 / 页码 / 每页条数变化都会触发 */
async function loadList(): Promise<void> {
  loading.value = true
  errorText.value = ''
  try {
    const res = await getOrthogroups({
      keyword: keyword.value,
      singleCopyOnly: singleCopyOnly.value,
      page: table.currentPage.value,
      pageSize: table.pageSize.value,
    })
    if (res.code !== 0) {
      errorText.value = res.message || t('global_search_error')
      rows.value = []
      serverTotal.value = 0
      return
    }
    rows.value = res.data.list
    serverTotal.value = res.data.total
  } catch (e) {
    errorText.value = e instanceof Error ? e.message : t('global_search_error')
    rows.value = []
    serverTotal.value = 0
  } finally {
    loading.value = false
  }
}

// 页码变化：重新取数
watch(table.currentPage, () => loadList())

// 每页条数变化：回到第一页再取数
watch(table.pageSize, () => {
  table.resetPage()
  loadList()
})

// 关键词防抖 300ms
let timer: ReturnType<typeof setTimeout> | null = null
watch(keyword, () => {
  if (timer) clearTimeout(timer)
  timer = setTimeout(() => {
    table.resetPage()
    loadList()
  }, 300)
})

// 单拷贝开关：立即重新取数
watch(singleCopyOnly, () => {
  table.resetPage()
  loadList()
})

// 首屏
void loadList()

// ============ 明细抽屉 ============
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<OrthogroupDetail | null>(null)

/** 打开某个 orthogroup 的明细 */
async function openDetail(row: Row): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const res = await getOrthogroupDetail(row.og_id)
    if (res.code === 0) detail.value = res.data
    else errorText.value = res.message || t('global_search_error')
  } catch {
    errorText.value = t('global_search_error')
  } finally {
    detailLoading.value = false
  }
}

// ============ 单拷贝基因 ============
const scgLoading = ref(false)
const scgList = ref<SingleCopyGene[]>([])
const scgLoaded = ref(false)

/** 加载单拷贝 orthogroup（按需加载，避免拖慢首屏） */
async function loadSingleCopy(): Promise<void> {
  if (scgLoaded.value) return
  scgLoading.value = true
  try {
    const res = await getSingleCopyGenes({ limit: 50 })
    if (res.code === 0) {
      scgList.value = res.data
      scgLoaded.value = true
    }
  } catch {
    errorText.value = t('global_search_error')
  } finally {
    scgLoading.value = false
  }
}
</script>

<template>
  <div class="container homology-page">
    <h2 class="mb-4">{{ t('module_homology') }}</h2>

    <!-- 数据说明：明确告知当前为预置数据，避免误导 -->
    <el-alert
      type="info"
      show-icon
      :closable="false"
      class="mb-4"
      :title="t('homology_mock_notice')"
    />

    <el-alert
      v-if="errorText"
      type="error"
      show-icon
      :closable="false"
      class="mb-4"
      :title="errorText"
    />

    <!-- 筛选区 -->
    <el-card class="mb-4">
      <div class="homology-filters">
        <el-input
          v-model="keyword"
          class="homology-filters__keyword"
          :placeholder="t('homology_keyword_placeholder')"
          clearable
          size="small"
        />
        <el-checkbox v-model="singleCopyOnly" size="small">
          {{ t('homology_single_copy_only') }}
        </el-checkbox>
      </div>
    </el-card>

    <!-- 列表 -->
    <el-card class="mb-4">
      <template #header>
        <div class="d-flex justify-content-between align-items-center">
          <span>{{ t('homology_orthogroups') }}</span>
          <el-tag type="primary">{{ t('total') }} {{ table.total }} {{ t('records') }}</el-tag>
        </div>
      </template>

      <TableToolbar
        v-model="keyword"
        :total="table.total"
        :columns="exportColumns"
        :rows="table.sortedRows"
        filename="orthogroups.csv"
        class="mb-3"
      />

      <el-table
        v-loading="loading"
        :data="table.pagedData"
        style="width: 100%"
        stripe
        border
        @sort-change="table.handleSortChange"
        @row-click="openDetail"
      >
        <el-table-column
          prop="og_id"
          :label="t('homology_orthogroup_id')"
          min-width="160"
          sortable="custom"
        />
        <el-table-column
          prop="species_count"
          :label="t('homology_species_count')"
          width="140"
          align="center"
          sortable="custom"
        />
        <el-table-column
          prop="gene_count"
          :label="t('homology_gene_count')"
          width="130"
          align="center"
          sortable="custom"
        />
        <el-table-column
          prop="is_single_copy"
          :label="t('homology_single_copy')"
          width="130"
          align="center"
          sortable="custom"
        >
          <template #default="scope">
            <el-tag :type="scope.row.is_single_copy ? 'success' : 'info'" size="small">
              {{ scope.row.is_single_copy ? t('yes') : t('no') }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="annotation" :label="t('homology_annotation')" min-width="220">
          <template #default="scope">
            {{ scope.row.annotation || '-' }}
          </template>
        </el-table-column>
      </el-table>

      <div v-if="table.total > table.pageSize" class="pagination-container">
        <el-pagination
          v-model:current-page="table.currentPage"
          v-model:page-size="table.pageSize"
          :page-sizes="table.pageSizes"
          layout="total, sizes, prev, pager, next, jumper"
          :total="table.total"
        />
      </div>
    </el-card>

    <!-- 单拷贝基因 -->
    <el-card class="mb-4">
      <template #header>
        <div class="d-flex justify-content-between align-items-center">
          <span>{{ t('homology_single_copy_genes') }}</span>
        </div>
      </template>

      <el-button
        type="primary"
        size="small"
        :loading="scgLoading"
        @click="loadSingleCopy"
      >
        {{ scgLoaded ? t('homology_loaded') : t('load') }}
      </el-button>

      <el-table v-if="scgList.length" :data="scgList" class="mt-3" stripe border>
        <el-table-column prop="og_id" :label="t('homology_orthogroup_id')" min-width="160" />
        <el-table-column :label="t('genes')" min-width="360">
          <template #default="scope">
            <span
              v-for="(g, idx) in scope.row.genes"
              :key="g.gene_id"
            >
              {{ g.gene_id }}<span v-if="idx === scope.row.genes.length - 1"> ({{ scope.row.genes.length }})</span>
            </span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else :description="t('no_data')" />
    </el-card>

    <!-- 明细抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="detail ? t('homology_orthogroup_id') + ': ' + detail.og_id : t('homology_orthogroup_id')"
      size="55%"
    >
      <div v-loading="detailLoading">
        <template v-if="detail">
          <el-descriptions :column="1" border class="mb-4">
            <el-descriptions-item :label="t('homology_orthogroup_id')">
              {{ detail.og_id }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_species_count')">
              {{ detail.species_count }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_gene_count')">
              {{ detail.gene_count }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_single_copy')">
              {{ detail.is_single_copy ? t('yes') : t('no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_annotation')">
              {{ detail.annotation || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <h4>{{ t('homology_genes') }}</h4>
          <el-table :data="detail.genes" stripe border>
            <el-table-column prop="gene_id" :label="t('gene')" min-width="200" />
            <el-table-column prop="genome_id" :label="t('genome')" min-width="220" />
          </el-table>
        </template>
        <el-empty v-else :description="t('no_data')" />
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.homology-page {
  max-width: 1200px;
  margin: 0 auto;
  padding-bottom: 2rem;
}

.homology-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.homology-filters__keyword {
  width: 260px;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.d-flex { display: flex; }
.justify-content-between { justify-content: space-between; }
.align-items-center { align-items: center; }
.mb-3 { margin-bottom: 1rem; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-3 { margin-top: 1rem; }
.mt-4 { margin-top: 1.5rem; }
</style>
