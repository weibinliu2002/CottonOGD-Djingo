<template>
  <div class="container-fluid">
    <div class="row">
      <div class="col-md-3">
        <div class="sidebar">
          <h3>{{ t('igv_view') }}</h3>

          <div class="mt-4">
            <h4 class="sidebar-title">{{ t('igv_select_genome') }}</h4>
            <el-cascader
              v-model="selectedGenome"
              :options="genomeOptions"
              :props="cascaderProps"
              :placeholder="t('select_genome')"
              class="w-100 mt-2"
              @change="handleGenomeChange"
              :loading="genomeLoading"
            />
          </div>

          <div class="mt-4">
            <h4 class="sidebar-title">{{ t('igv_locus') }}</h4>
            <el-input
              v-model="locusInput"
              :placeholder="'e.g. Ghir_A01:1-1000000'"
              class="mt-2"
              @keyup.enter="handleLoad"
            />
          </div>

          <div class="mt-4 d-grid gap-2">
            <button class="btn btn-primary" @click="handleLoad" :disabled="loading">
              {{ t('igv_load') }}
            </button>
            <button class="btn btn-secondary" @click="handleReset" :disabled="loading">
              {{ t('igv_reset') }}
            </button>
          </div>
        </div>
      </div>

      <div class="col-md-9">
        <div class="main-content">
          <h2>{{ t('igv_visualization') }}</h2>
          <div v-if="selectedGenomeName" class="genome-info">
            <p><strong>{{ t('genome') }}:</strong> {{ selectedGenomeName }}</p>
          </div>

          <el-alert
            v-if="errorMessage"
            type="error"
            :title="errorMessage"
            show-icon
            class="mb-3"
            @close="errorMessage = ''"
          />

          <el-alert
            v-if="loading"
            type="info"
            :title="t('igv_loading')"
            show-icon
            class="mb-3"
          />

          <div class="igv-container-wrap">
            <div ref="igvContainer" class="igv-container"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import igv from 'igv'
import {
  buildGenomeDataPaths,
  createDefaultLocus,
  useGenomeSelector
} from '@/composables/useGenomeBrowser'

const DEFAULT_WINDOW = '1-1000000'

const { t } = useI18n()
const {
  selectedGenome,
  selectedGenomeName,
  genomeOptions,
  genomeLoading,
  cascaderProps,
  ensureGenomesLoaded,
  pickDefaultGenome,
  setSelectedGenome,
  extractGenomeName
} = useGenomeSelector()

const igvContainer = ref(null)
const browser = ref(null)
const loading = ref(false)
const errorMessage = ref('')

const locusInput = ref('')

const destroyBrowser = () => {
  if (browser.value && typeof browser.value.dispose === 'function') {
    browser.value.dispose()
  }
  browser.value = null

  if (igvContainer.value) {
    igvContainer.value.innerHTML = ''
  }
}

const createBrowser = async (genomeName, locus) => {
  const { fastaURL, faiURL, gffURL, gffIndexURL } = buildGenomeDataPaths(genomeName)

  destroyBrowser()
  await nextTick()

  browser.value = await igv.createBrowser(igvContainer.value, {
    locus,
    reference: {
      id: genomeName,
      name: genomeName,
      fastaURL,
      indexURL: faiURL
    },
    tracks: [
      {
        name: 'Gene Annotation',
        type: 'annotation',
        format: 'gff3',
        url: gffURL,
        indexURL: gffIndexURL
      }
    ]
  })
}

const loadGenome = async (genomeName, preferredLocus = '') => {
  if (!genomeName) return

  loading.value = true
  errorMessage.value = ''

  try {
    const locus = preferredLocus.trim()
      ? preferredLocus.trim()
      : await createDefaultLocus(genomeName, DEFAULT_WINDOW, 'chr1')
    await createBrowser(genomeName, locus)
    locusInput.value = locus
  } catch (error) {
    const details = error?.message || String(error)
    errorMessage.value = `${t('igv_load_failed')}: ${genomeName}. ${details}`
  } finally {
    loading.value = false
  }
}

const handleGenomeChange = async (value) => {
  const genomeName = extractGenomeName(value)
  if (!genomeName) return
  await loadGenome(genomeName)
}

const handleLoad = async () => {
  if (!selectedGenomeName.value) {
    errorMessage.value = t('please_select_genome')
    return
  }

  await loadGenome(selectedGenomeName.value, locusInput.value)
}

const handleReset = async () => {
  if (!selectedGenomeName.value) return
  locusInput.value = ''
  await loadGenome(selectedGenomeName.value, '')
}

onMounted(async () => {
  await ensureGenomesLoaded()

  const defaultGenome = pickDefaultGenome()
  if (!defaultGenome) {
    errorMessage.value = t('no_genome_data_available')
    return
  }

  setSelectedGenome(defaultGenome)
  await loadGenome(defaultGenome)
})

onBeforeUnmount(() => {
  destroyBrowser()
})
</script>

<style scoped>
.container-fluid {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.sidebar {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  height: fit-content;
}

.sidebar h3 {
  font-size: 1.2rem;
  font-weight: 700;
  color: #333;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: 700;
  color: #333;
  margin-bottom: 0;
}

.main-content {
  background-color: #fff;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.main-content h2 {
  font-size: 1.5rem;
  font-weight: 700;
  color: #333;
}

.genome-info {
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 6px;
  font-size: 0.9rem;
  margin-bottom: 16px;
}

.igv-container-wrap {
  border: 1px solid #e0e0e0;
  border-radius: 6px;
  overflow: hidden;
  min-height: 800px;
  background: #fff;
}

.igv-container {
  width: 100%;
  height: 800px;
}

@media (max-width: 768px) {
  .container-fluid {
    padding: 10px;
  }

  .sidebar,
  .main-content {
    padding: 15px;
    margin-bottom: 20px;
  }

  .igv-container-wrap,
  .igv-container {
    min-height: 620px;
    height: 620px;
  }
}
</style>
