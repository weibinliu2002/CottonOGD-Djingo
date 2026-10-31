<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('genome_synteny') }}</h2>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('genome_variation_search') }}</span>
        </div>
      </template>

      <el-form @submit.prevent="handleSubmit" label-width="200px">
        <el-form-item :label="t('reference_genome')">
          <el-tree-select
            v-model="referenceGenome"
            :data="genomeOptions"
            :props="{ value: 'value', label: 'label', children: 'children' }"
            :placeholder="t('select_reference_genome')"
            style="width: 100%"
            :loading="genomeLoading"
          />
        </el-form-item>

        <el-form-item :label="t('query_genome')">
          <el-tree-select
            v-model="queryGenome"
            :data="genomeOptions"
            :props="{ value: 'value', label: 'label', children: 'children' }"
            :placeholder="t('select_query_genome')"
            style="width: 100%"
            :loading="genomeLoading"
          />
        </el-form-item>

        <el-form-item :label="t('chromosome')">
          <el-input
            v-model="chromosome"
            :placeholder="t('chromosome_placeholder')"
          />
        </el-form-item>

        <el-form-item :label="t('variation_type')">
          <el-select v-model="variationType" :placeholder="t('select_variation_type')" style="width: 100%">
            <el-option value="DUP" label="DUP (Duplication)" />
            <el-option value="DEL" label="DEL (Deletion)" />
            <el-option value="INV" label="INV (Inversion)" />
            <el-option value="TRA" label="TRA (Translocation)" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="info" size="small" @click="fillExample">
            {{ t('load_example') }}
          </el-button>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="store.syntenyLoading">
            <el-icon><Search /></el-icon>
            {{ t('search') }}
          </el-button>
        </el-form-item>

        <el-alert
          v-if="store.syntenyError"
          :title="store.syntenyError"
          type="error"
          show-icon
          class="mt-3"
          @close="store.clearSynteny()"
        />
      </el-form>
    </el-card>

    <el-card v-if="store.syntenyResult" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ t('synteny_results') }}</span>
          <div>
            <el-tag type="info" class="mr-2">
              {{ t('ref') }}: {{ store.syntenyResult.reference_genome }}
            </el-tag>
            <el-tag type="info" class="mr-2">
              {{ t('query') }}: {{ store.syntenyResult.query_genome }}
            </el-tag>
            <el-tag type="info" class="mr-2">
              {{ t('chromosome') }}: {{ store.syntenyResult.chromosome }}
            </el-tag>
            <el-tag type="success">
              {{ t('found') }} {{ store.syntenyResult.ref_gene_count }} {{ t('variations') }}
            </el-tag>
          </div>
        </div>
      </template>

      <el-table
        :data="table.pagedData"
        style="width: 100%"
        stripe
        @sort-change="table.handleSortChange"
      >
        <el-table-column prop="id" :label="t('id')" width="80" sortable="custom" />
        <el-table-column prop="Ref_genome_chr" :label="t('reference_position')" width="220" sortable="custom">
          <template #default="scope">
            {{ scope.row.Ref_genome_chr }}:{{ scope.row.Ref_genome_start }}-{{ scope.row.Ref_genome_end }}
          </template>
        </el-table-column>
        <el-table-column prop="Query_genome_chr" :label="t('query_position')" width="220" sortable="custom">
          <template #default="scope">
            {{ scope.row.Query_genome_chr }}:{{ scope.row.Query_genome_start }}-{{ scope.row.Query_genome_end }}
          </template>
        </el-table-column>
        <el-table-column prop="Variation_type" :label="t('variation_type')" width="140" sortable="custom" />
        <el-table-column prop="son_type" :label="t('sub_type')" width="120" sortable="custom" />
        <el-table-column prop="copygain" :label="t('copy_gain')" width="120" sortable="custom">
          <template #default="scope">
            <el-tag :type="scope.row.copygain === 'copygain' ? 'success' : 'danger'" size="small">
              {{ scope.row.copygain }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="Parent_Variation" :label="t('parent_variation')" width="150" sortable="custom" />
        <el-table-column prop="Ref_seq" :label="t('ref_seq')" width="100" sortable="custom" />
        <el-table-column prop="Alt_seq" :label="t('alt_seq')" width="100" sortable="custom" />
      </el-table>

      <!-- 关键词筛选 + 计数 + 导出（阶段 3.2 新增） -->
      <TableToolbar
        v-model="table.keyword"
        :total="table.total"
        :columns="syntenyExportColumns"
        :rows="table.sortedRows"
        filename="genome_synteny_results.csv"
        class="mt-3"
      />

      <!-- 分页（阶段 3.2 新增：原页面无分页，共线基因多时无法浏览） -->
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
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { useEnrichmentStore } from '@/stores/modules/enrichment'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { useEnhancedTable } from '@/composables/core/useEnhancedTable'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()
const store = useEnrichmentStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

/**
 * 表格增强（阶段 3.2）
 *
 * 共线基因列表原先全量渲染、无分页；这里叠加筛选 / 排序 / 分页 / 导出。
 * 数据源仍为 store.syntenyResult.reference_genes，取数逻辑不动。
 */
type SyntenyRow = Record<string, any>

const table = useEnhancedTable<SyntenyRow>(
  () => (store.syntenyResult?.reference_genes ?? []) as SyntenyRow[],
  {
    pageSize: 10,
    pageSizes: [10, 20, 50, 100],
    searchFields: ['Ref_genome_chr', 'Query_genome_chr', 'Variation_type', 'son_type', 'copygain'],
  },
)

/** 导出列定义 */
const syntenyExportColumns: ExportColumn<SyntenyRow>[] = [
  { key: 'id', label: 'ID' },
  {
    key: 'Ref_genome_chr',
    label: 'Reference Position',
    formatter: (row) => `${row.Ref_genome_chr}:${row.Ref_genome_start}-${row.Ref_genome_end}`,
  },
  {
    key: 'Query_genome_chr',
    label: 'Query Position',
    formatter: (row) => `${row.Query_genome_chr}:${row.Query_genome_start}-${row.Query_genome_end}`,
  },
  { key: 'Variation_type', label: 'Variation Type' },
  { key: 'son_type', label: 'Sub Type' },
  { key: 'copygain', label: 'Copy Gain' },
  { key: 'Parent_Variation', label: 'Parent Variation' },
  { key: 'Ref_seq', label: 'Ref Seq' },
  { key: 'Alt_seq', label: 'Alt Seq' },
]

const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()

const referenceGenome = ref('')
const queryGenome = ref('')
const chromosome = ref('')
const variationType = ref('DUP')

onMounted(async () => {
  await ensureGenomesLoaded()
  const defaultGenome = pickDefaultGenome()
  if (defaultGenome) {
    referenceGenome.value = defaultGenome
  }
})

const fillExample = () => {
  referenceGenome.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  queryGenome.value = 'G.hirsutumAD1_Jin668_HAU_v1T2T'
  chromosome.value = 'Ghir_A01'
  variationType.value = 'DUP'
}

const handleSubmit = async () => {
  if (!referenceGenome.value) {
    store.syntenyError = t('please_select_reference_genome')
    return
  }
  if (!queryGenome.value) {
    store.syntenyError = t('please_select_query_genome')
    return
  }
  if (!chromosome.value.trim()) {
    store.syntenyError = t('please_enter_chromosome')
    return
  }

  showLoading?.()
  try {
    await store.searchGenomeSynteny(
      referenceGenome.value,
      queryGenome.value,
      chromosome.value,
      variationType.value
    )
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
.mr-2 { margin-right: 0.5rem; }

.card-header {
  font-size: 16px;
  font-weight: 500;
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
