<template>
  <div class="container mt-4">
    <h2 class="mb-4">{{ t('gene_location') }}</h2>

    <el-card class="mb-4">
      <template #header>
        <div class="card-header">
          <span>{{ t('gene_genomic_distribution') }}</span>
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

        <el-form-item :label="t('gene_ids')">
          <el-input
            type="textarea"
            :rows="6"
            v-model="geneIds"
            :placeholder="t('gene_ids_placeholder')"
          />
          <div class="mt-2">
            <el-button type="info" size="small" @click="fillExample">
              {{ t('load_example') }}
            </el-button>
          </div>
          <div class="text-muted mt-1">{{ t('gene_ids_format_hint') }}</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="store.geneLocationLoading">
            <el-icon><Search /></el-icon>
            {{ t('search') }}
          </el-button>
        </el-form-item>

        <el-alert
          v-if="store.geneLocationError"
          :title="store.geneLocationError"
          type="error"
          show-icon
          class="mt-3"
          @close="store.clearGeneLocation()"
        />
      </el-form>
    </el-card>

    <template v-if="store.geneLocationResult">
      <el-card class="mb-4">
        <template #header>
          <div class="card-header d-flex justify-content-between align-items-center">
            <span>{{ t('chromosome_distribution') }}</span>
            <el-tag type="info">
              {{ t('genome') }}: {{ store.geneLocationResult.genome }} |
              {{ t('total_genes') }}: {{ store.geneLocationResult.total_genes }}
            </el-tag>
          </div>
        </template>

        <div class="distribution-chart">
          <div
            v-for="(count, chr) in store.geneLocationResult.chr_distribution"
            :key="chr"
            class="chr-bar-row"
          >
            <span class="chr-label">{{ chr }}</span>
            <div class="chr-bar-track">
              <div
                class="chr-bar-fill"
                :style="{ width: getBarWidth(count) + '%' }"
              />
            </div>
            <span class="chr-count">{{ count }}</span>
          </div>
        </div>
      </el-card>

      <el-card class="mb-4">
        <template #header>
          <div class="card-header d-flex justify-content-between align-items-center">
            <span>{{ t('gene_location_details') }}</span>
            <el-button type="primary" size="small" @click="downloadTable">
              {{ t('download_table') }}
            </el-button>
          </div>
        </template>

        <el-table :data="store.geneLocationResult.gene_locations" style="width: 100%" stripe>
          <el-table-column prop="gene_id" :label="t('gene_id')" width="200" />
          <el-table-column prop="chr" :label="t('chromosome')" width="150" />
          <el-table-column prop="start" :label="t('start_position')" width="150" />
          <el-table-column prop="end" :label="t('end_position')" width="150" />
          <el-table-column prop="strand" :label="t('strand')" width="100" />
          <el-table-column :label="t('length')" width="120">
            <template #default="scope">
              {{ (scope.row.end - scope.row.start + 1).toLocaleString() }}
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </template>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { useEnrichmentStore } from '@/stores/enrichmentStore'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'

const { t } = useI18n()
const store = useEnrichmentStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()

const selectedGenome = ref('')
const geneIds = ref('')

const maxCount = computed(() => {
  if (!store.geneLocationResult) return 0
  return Math.max(...Object.values(store.geneLocationResult.chr_distribution))
})

const getBarWidth = (count: number) => {
  if (maxCount.value === 0) return 0
  return (count / maxCount.value) * 100
}

onMounted(async () => {
  await ensureGenomesLoaded()
  const defaultGenome = pickDefaultGenome()
  if (defaultGenome) {
    selectedGenome.value = defaultGenome
  }
})

const fillExample = () => {
  selectedGenome.value = 'G.hirsutumAD1_TM-1_HAU_v1.1'
  geneIds.value = 'Ghir_D05G000260.1,Ghir_D05G000360.1,Ghir_D05G000360.2'
}

const handleSubmit = async () => {
  if (!selectedGenome.value) {
    store.geneLocationError = t('please_select_genome')
    return
  }
  if (!geneIds.value.trim()) {
    store.geneLocationError = t('please_enter_gene_ids')
    return
  }

  showLoading?.()
  try {
    await store.searchGeneLocation(selectedGenome.value, geneIds.value)
  } finally {
    hideLoading?.()
  }
}

const downloadTable = () => {
  if (!store.geneLocationResult) return

  const header = ['Gene ID', 'Chromosome', 'Start', 'End', 'Strand', 'Length'].join('\t')
  const rows = store.geneLocationResult.gene_locations.map(g =>
    [g.gene_id, g.chr, g.start, g.end, g.strand, g.end - g.start + 1].join('\t')
  )
  const content = [header, ...rows].join('\n')

  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = 'gene_location.txt'
  a.click()
  URL.revokeObjectURL(url)
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
.mt-2 { margin-top: 0.5rem; }
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

.distribution-chart {
  padding: 10px 0;
}

.chr-bar-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.chr-label {
  width: 120px;
  font-size: 13px;
  font-weight: 500;
  text-align: right;
  padding-right: 12px;
  flex-shrink: 0;
}

.chr-bar-track {
  flex: 1;
  height: 24px;
  background: #f0f2f5;
  border-radius: 4px;
  overflow: hidden;
}

.chr-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #409eff, #67c23a);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.chr-count {
  width: 60px;
  font-size: 13px;
  font-weight: 500;
  text-align: left;
  padding-left: 10px;
  flex-shrink: 0;
}
</style>
