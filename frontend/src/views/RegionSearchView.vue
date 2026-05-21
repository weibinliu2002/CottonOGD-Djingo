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

      <el-table :data="store.regionSearchResult.genes" style="width: 100%">
        <el-table-column prop="geneid_id" :label="t('gene_id')" width="200">
          <template #default="scope">
            <a href="javascript:void(0)" @click="navigateToGeneDetail(scope.row)">
              {{ scope.row.geneid_id }}
            </a>
          </template>
        </el-table-column>
        <el-table-column prop="seqid" :label="t('chromosome')" width="150" />
        <el-table-column prop="start" :label="t('start_position')" width="150" />
        <el-table-column prop="end" :label="t('end_position')" width="150" />
        <el-table-column prop="strand" :label="t('strand')" width="100" />
        <el-table-column prop="type" :label="t('type')" width="100" />
      </el-table>
    </el-card>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { useEnrichmentStore } from '@/stores/enrichmentStore'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import { useNavigationStore } from '@/stores/navigationStore'
import { useGeneSearchStore } from '@/stores/geneSearch'
import httpInstance from '@/utils/http'

const { t } = useI18n()
const router = useRouter()
const store = useEnrichmentStore()
const navigationStore = useNavigationStore()
const geneSearchStore = useGeneSearchStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()

const selectedGenome = ref('')
const region = ref('')

onMounted(async () => {
  await ensureGenomesLoaded()
  const defaultGenome = pickDefaultGenome()
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
</style>
