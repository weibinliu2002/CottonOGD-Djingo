<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('region_search') }}</h2>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('search_by_genomic_region') }}</span>
        </div>
      </template>

      <el-form @submit.prevent="handleSubmit" label-width="180px">
        <el-form-item :label="t('select_genome')">
          <el-tree-select
            v-model="selectedGenome"
            :data="genomeOptions"
            :props="{ value: 'value', label: 'label', children: 'children' }"
            :placeholder="t('select_genome')"
            style="width: 100%"
            :loading="genomeLoading"
          />
        </el-form-item>

        <el-form-item :label="t('genomic_region')">
          <el-input
            v-model="region"
            :placeholder="t('region_placeholder')"
          />
          <div class="text-muted mt-1">{{ t('region_format_hint') }}</div>
        </el-form-item>

        <el-form-item>
          <el-button type="info" size="small" @click="fillExample">
            {{ t('load_example') }}
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="store.regionSearchLoading">
            <el-icon><Search /></el-icon>
            {{ t('search') }}
          </el-button>
        </el-form-item>

        <el-alert
          v-if="store.regionSearchError"
          :title="store.regionSearchError"
          type="error"
          show-icon
          class="mt-3"
          @close="store.clearRegionSearch()"
        />
      </el-form>
    </el-card>

    <el-card v-if="store.regionSearchResult" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ t('region_search_results') }}</span>
          <el-tag type="info">
            {{ t('genome') }}: {{ store.regionSearchResult.genome }} |
            {{ t('region') }}: {{ store.regionSearchResult.region }} |
            {{ t('found') }} {{ store.regionSearchResult.count }} {{ t('genes') }}
          </el-tag>
        </div>
      </template>

      <el-table
        :data="table.pagedData"
        style="width: 100%"
        @sort-change="table.handleSortChange"
      >
        <el-table-column prop="geneid_id" :label="t('gene_id')" width="200" sortable="custom">
          <template #default="scope">
            <a href="javascript:void(0)" @click="navigateToGeneDetail(scope.row)">
              {{ scope.row.geneid_id }}
            </a>
          </template>
        </el-table-column>
        <el-table-column prop="seqid" :label="t('chromosome')" width="150" sortable="custom" />
        <el-table-column prop="start" :label="t('start_position')" width="150" sortable="custom" />
        <el-table-column prop="end" :label="t('end_position')" width="150" sortable="custom" />
        <el-table-column prop="strand" :label="t('strand')" width="100" sortable="custom" />
        <el-table-column prop="type" :label="t('type')" width="100" sortable="custom" />
      </el-table>

      <!-- 关键词筛选 + 计数 + 导出（阶段 3.2 新增） -->
      <TableToolbar
        v-model="table.keyword"
        :total="table.total"
        :columns="regionExportColumns"
        :rows="table.sortedRows"
        filename="region_search_results.csv"
        class="mt-3"
      />

      <!-- 分页（阶段 3.2 新增：原页面无分页，区间内基因多时无法浏览） -->
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

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { useEnrichmentStore } from '@/stores/modules/enrichment'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { useNavigationStore } from '@/stores/modules/navigation'
import { useGeneSearchStore } from '@/stores/modules/geneSearch'
import httpInstance from '@/utils/http.js'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const store = useEnrichmentStore()
const navigationStore = useNavigationStore()
const geneSearchStore = useGeneSearchStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome, allGenomes } = useGenomeSelector()

const selectedGenome = ref('')
const region = ref('')

/**
 * 表格增强（阶段 3.2）
 *
 * 区间检索结果原先全量渲染、无分页；这里叠加筛选 / 排序 / 分页 / 导出。
 * 数据源仍为 store.regionSearchResult.genes，取数逻辑不动。
 */
type RegionRow = Record<string, any>

const table = useEnhancedTable<RegionRow>(
  () => (store.regionSearchResult?.genes ?? []) as RegionRow[],
  {
    pageSize: 10,
    pageSizes: [10, 20, 50, 100],
    searchFields: ['geneid_id', 'seqid', 'type', 'strand'],
  },
)

/** 导出列定义 */
const regionExportColumns: ExportColumn<RegionRow>[] = [
  { key: 'geneid_id', label: 'Gene ID' },
  { key: 'seqid', label: 'Chromosome' },
  { key: 'start', label: 'Start' },
  { key: 'end', label: 'End' },
  { key: 'strand', label: 'Strand' },
  { key: 'type', label: 'Type' },
]

onMounted(async () => {
  await ensureGenomesLoaded()
  const queryGenome = typeof route.query.genome === 'string' ? route.query.genome : ''
  const defaultGenome = queryGenome && allGenomes.value.includes(queryGenome)
    ? queryGenome
    : pickDefaultGenome()
  if (defaultGenome) {
    selectedGenome.value = defaultGenome
  }
})

const fillExample = () => {
  selectedGenome.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  region.value = 'Ghir_A01:20260371-20686979'
}

const handleSubmit = async () => {
  if (!selectedGenome.value) {
    store.regionSearchError = t('please_select_genome')
    return
  }
  if (!region.value.trim()) {
    store.regionSearchError = t('please_enter_region')
    return
  }

  showLoading?.()
  try {
    await store.searchByRegion(selectedGenome.value, region.value)
  } finally {
    hideLoading?.()
  }
}

const navigateToGeneDetail = async (gene: any) => {
  showLoading?.()
  try {
    const geneId = gene.geneid_id
    const genomeId = store.regionSearchResult?.genome || selectedGenome.value
    const requestId = 'region_search'

    const params = {
      gene_id: geneId,
      genome_id: genomeId,
      request_id: requestId
    }

    const response = await httpInstance.post('/CottonOGD_api/geneid_summary/', params) as any

    if (response && response.geneid_result) {
      const searchResults = {
        geneid_result: typeof response.geneid_result === 'string' ? JSON.parse(response.geneid_result) : response.geneid_result,
        gene_info_result: typeof response.gene_info_result === 'string' ? JSON.parse(response.gene_info_result) : response.gene_info_result,
        search_map: typeof response.search_map === 'string' ? JSON.parse(response.search_map) : response.search_map,
        gene_go_result: response.gene_go_result || [],
        gene_kegg_result: response.gene_kegg_result || []
      }

      const dbIds = searchResults.search_map
        ? Object.values(searchResults.search_map).map((item: any) => item.db_id).filter(Boolean)
        : []

      navigationStore.setNavigationData('geneSearch', {
        results: searchResults,
        dbIds: dbIds,
        requestId: requestId
      })

      router.push({ name: 'idSearchSummary' })
    }
  } catch (e: any) {
    console.error('Navigation to gene detail failed:', e)
  } finally {
    hideLoading?.()
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}

.mt-4 { margin-top: 1.5rem; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-3 { margin-top: 1rem; }
.mt-1 { margin-top: 0.25rem; }

.card-header {
  font-size: 16px;
  font-weight: 500;
}

.text-muted {
  color: #6c757d;
  font-size: 0.85rem;
}

.d-flex { display: flex; }
.justify-content-between { justify-content: space-between; }
.align-items-center { align-items: center; }

/* 分页容器（阶段 3.2 新增分页条） */
.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}
</style>
