<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('variome_genotype') }}</h2>
    <p class="text-muted mb-4">{{ t('module_variome_desc') }}</p>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">{{ t('genotype_matrix') }}</div>
      </template>

      <el-form @submit.prevent="handleSubmit" label-width="180px">
        <el-form-item :label="t('select_dataset')">
          <el-select v-model="setId" :placeholder="t('select_dataset')" style="width: 100%" :loading="setsLoading">
            <el-option v-for="s in sets" :key="s.id" :label="`${s.name} (${s.sample_count} samples)`" :value="s.id" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('chromosome')">
          <el-input v-model="chromosome" :placeholder="t('chromosome')" />
        </el-form-item>

        <el-form-item>
          <div class="d-flex gap-2">
            <el-input v-model="start" :placeholder="t('region_start')" style="width: 180px" />
            <span class="align-self-center">-</span>
            <el-input v-model="end" :placeholder="t('region_end')" style="width: 180px" />
          </div>
          <div class="text-muted mt-1">{{ t('region_format_hint') }}</div>
        </el-form-item>

        <el-form-item :label="t('input_samples')">
          <el-input v-model="samplesText" type="textarea" :rows="2" :placeholder="t('input_samples')" />
        </el-form-item>

        <el-form-item :label="t('genotype_format')">
          <el-input v-model="format" :placeholder="t('format')" style="width: 200px" />
        </el-form-item>

        <el-form-item>
          <el-button type="info" size="small" @click="fillExample">{{ t('load_example') }}</el-button>
          <el-button type="primary" :loading="loading" class="ms-2" @click="handleSubmit">
            <el-icon><Search /></el-icon>{{ t('search') }}
          </el-button>
        </el-form-item>

        <el-alert v-if="error" :title="error" type="error" show-icon class="mt-3" @close="error = ''" />
      </el-form>
    </el-card>

    <el-card v-if="rows.length" class="mb-4">
      <template #header>
        <div class="card-header d-flex justify-content-between align-items-center">
          <span>{{ t('genotype_matrix') }}</span>
          <el-tag type="info">{{ t('found') }} {{ rows.length }} {{ t('records') }}</el-tag>
        </div>
      </template>

      <el-table :data="rows" style="width: 100%" max-height="600">
        <el-table-column prop="chrom" :label="t('chromosome')" width="100" fixed />
        <el-table-column prop="pos" :label="t('position')" width="120" fixed />
        <el-table-column prop="ref" :label="t('ref')" width="70" fixed />
        <el-table-column prop="alt" :label="t('alt')" width="70" fixed />
        <el-table-column v-for="col in sampleCols" :key="col" :prop="col" :label="col" width="100" />
      </el-table>

      <TableToolbar
        v-model="keyword"
        :total="rows.length"
        :columns="exportColumns"
        :rows="rows"
        filename="genotype_matrix.csv"
        class="mt-3"
      />
    </el-card>

    <el-empty v-else-if="searched && !loading" :description="t('no_data')" />

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import {
  getVariantSets,
  getVariantGenotype,
  type VariantSet,
  type VariantGenotypeResult,
} from '@/api/index'
import TableToolbar from '@/components/data-display/TableToolbar.vue'
import type { ExportColumn } from '@/utils/exportTable'

const { t } = useI18n()

const sets = ref<VariantSet[]>([])
const setsLoading = ref(false)
const setId = ref<number | undefined>(undefined)
const chromosome = ref('')
const start = ref<number | undefined>(undefined)
const end = ref<number | undefined>(undefined)
const samplesText = ref('')
const format = ref('GT')
const loading = ref(false)
const searched = ref(false)
const error = ref('')
const keyword = ref('')

const sampleCols = ref<string[]>([])
const rows = ref<Record<string, any>[]>([])

onMounted(async () => {
  setsLoading.value = true
  try {
    const res = await getVariantSets()
    sets.value = res.data ?? []
    if (sets.value.length) setId.value = sets.value[0].id
  } catch (e) {
    error.value = String(e)
  } finally {
    setsLoading.value = false
  }
})

const fillExample = () => {
  if (sets.value.length) setId.value = sets.value[0].id
  chromosome.value = 'A01'
  start.value = 1
  end.value = 100000
}

const buildRows = (data: VariantGenotypeResult) => {
  // 后端返回 {samples:[...], records:[{chrom,pos,ref,alt,id?,genotypes:{sample:gt}}]}
  // genotypes 按样本展开为列
  sampleCols.value = data.samples ?? []
  rows.value = data.records.map((d) => ({
    chrom: d.chrom,
    pos: d.pos,
    ref: d.ref,
    alt: d.alt,
    ...(d.genotypes ?? {}),
  }))
}

const exportColumns = computed<ExportColumn<Record<string, any>>[]>(() => [
  { key: 'chrom', label: 'Chrom' },
  { key: 'pos', label: 'Pos' },
  { key: 'ref', label: 'Ref' },
  { key: 'alt', label: 'Alt' },
  ...sampleCols.value.map((c) => ({ key: c, label: c })),
])

const handleSubmit = async () => {
  if (setId.value === undefined) {
    error.value = t('select_dataset')
    return
  }
  if (!chromosome.value) {
    error.value = t('chromosome')
    return
  }
  if (start.value === undefined || end.value === undefined) {
    error.value = t('region_format_hint')
    return
  }
  loading.value = true
  searched.value = false
  error.value = ''
  try {
    const res = await getVariantGenotype({
      set_id: setId.value,
      chrom: chromosome.value,
      start: start.value,
      end: end.value,
      samples: samplesText.value ? samplesText.value.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
      format: format.value || undefined,
    })
    const data = res.data
    // 区间上限提示（文档建议 ≤ 1Mb）
    if (end.value - start.value > 1000000) {
      error.value = t('region_too_large')
    }
    if (data) {
      buildRows(data)
    } else {
      sampleCols.value = []
      rows.value = []
    }
    searched.value = true
  } catch (e: any) {
    error.value = e?.message || String(e)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.container { max-width: 1200px; margin: 0 auto; padding: 0 15px; }
.mt-4 { margin-top: 1.5rem; }
.mb-4 { margin-bottom: 1.5rem; }
.mt-3 { margin-top: 1rem; }
.mt-1 { margin-top: 0.25rem; }
.card-header { font-size: 16px; font-weight: 500; }
.text-muted { color: #6c757d; font-size: 0.85rem; }
.d-flex { display: flex; }
.gap-2 { gap: 0.5rem; }
.align-self-center { align-self: center; }
.ms-2 { margin-left: 0.5rem; }
</style>
