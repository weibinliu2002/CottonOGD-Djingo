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
              Load / Reload
            </button>
            <button class="btn btn-secondary reset-action-btn" @click="handleReset" :disabled="loading">
              {{ t('igv_reset') }}
            </button>
          </div>

          <div class="mt-4 track-panel">
            <h4 class="sidebar-title">Tracks</h4>

            <div class="track-item">
              <el-switch
                v-model="defaultAnnotationEnabled"
                active-text="Gene Annotation"
                @change="handleDefaultTrackToggle"
              />
            </div>

            <div class="track-form mt-3">
              <el-input v-model="customTrackForm.name" placeholder="Track name" class="mb-2" />
              <el-select v-model="customTrackForm.type" class="w-100 mb-2">
                <el-option label="annotation" value="annotation" />
                <el-option label="alignment" value="alignment" />
                <el-option label="variant" value="variant" />
                <el-option label="wig" value="wig" />
              </el-select>
              <el-input v-model="customTrackForm.format" placeholder="Format (gff3/bam/vcf...)" class="mb-2" />
              <el-input v-model="customTrackForm.url" placeholder="Track URL" class="mb-2" />
              <el-input v-model="customTrackForm.indexURL" placeholder="Index URL (optional)" class="mb-2" />
              <button class="btn btn-outline-primary w-100" @click="handleAddCustomTrack" :disabled="loading">
                Add Track
              </button>
            </div>

            <ul v-if="customTracks.length" class="custom-track-list mt-3">
              <li v-for="(track, index) in customTracks" :key="`${track.url}-${index}`" class="custom-track-item">
                <span class="track-name">{{ track.name }}</span>
                <button class="btn btn-sm btn-outline-danger" @click="handleRemoveCustomTrack(index)">Remove</button>
              </li>
            </ul>
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
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, inject } from 'vue'
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
const showLoading = inject('showLoading')
const hideLoading = inject('hideLoading')

const igvContainer = ref(null)
const browser = ref(null)
const loading = ref(false)
const errorMessage = ref('')
let latestLoadToken = 0

const locusInput = ref('')
const defaultAnnotationEnabled = ref(true)
const customTracks = ref([])
const customTrackForm = ref({
  name: '',
  type: 'annotation',
  format: 'gff3',
  url: '',
  indexURL: ''
})

const destroyBrowser = () => {
  if (browser.value && typeof browser.value.dispose === 'function') {
    browser.value.dispose()
  }
  browser.value = null

  if (igvContainer.value) {
    igvContainer.value.innerHTML = ''
  }
}

const createBrowser = async (genomeName, locus, token) => {
  // 首先检查token是否有效
  if (token !== latestLoadToken) return
  
  const { fastaURL, faiURL, gffURL, gffIndexURL } = buildGenomeDataPaths(genomeName)
  const tracks = []

  if (defaultAnnotationEnabled.value) {
    tracks.push({
      name: 'Gene Annotation',
      type: 'annotation',
      format: 'gff3',
      url: gffURL,
      indexURL: gffIndexURL
    })
  }

  customTracks.value.forEach((track) => {
    tracks.push({ ...track })
  })

  // 销毁旧的浏览器实例
  destroyBrowser()
  
  // 等待DOM更新
  await nextTick()
  
  // 再次检查token
  if (token !== latestLoadToken) return

  try {
    const newBrowser = await igv.createBrowser(igvContainer.value, {
      locus,
      reference: {
        id: genomeName,
        name: genomeName,
        fastaURL,
        indexURL: faiURL
      },
      tracks
    })

    // 再次检查token，确保只保留最新的浏览器实例
    if (token !== latestLoadToken) {
      if (newBrowser && typeof newBrowser.dispose === 'function') {
        newBrowser.dispose()
      }
      return
    }

    browser.value = newBrowser
  } catch (error) {
    console.error('Error creating IGV browser:', error)
    throw error
  }
}

const loadGenome = async (genomeName, preferredLocus = '') => {
  if (!genomeName) return

  const token = ++latestLoadToken
  showLoading?.()
  loading.value = true
  errorMessage.value = ''

  try {
    // 确保只处理最新的请求
    if (token !== latestLoadToken) return
    
    const locus = preferredLocus.trim()
      ? preferredLocus.trim()
      : await createDefaultLocus(genomeName, DEFAULT_WINDOW, 'chr1')
    
    // 再次检查token，因为createDefaultLocus可能是异步的
    if (token !== latestLoadToken) return
    
    await createBrowser(genomeName, locus, token)
    if (token !== latestLoadToken) return
    locusInput.value = locus
  } catch (error) {
    if (token !== latestLoadToken) return
    const details = error?.message || String(error)
    errorMessage.value = `${t('igv_load_failed')}: ${genomeName}. ${details}`
  } finally {
    if (token === latestLoadToken) {
      loading.value = false
      hideLoading?.()
    }
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

  try {
    await loadGenome(selectedGenomeName.value, locusInput.value)
  } catch (error) {
    console.error('Error in handleLoad:', error)
    errorMessage.value = `Failed to load IGV: ${error?.message || String(error)}`
  }
}

const handleReset = async () => {
  if (!selectedGenomeName.value) return
  locusInput.value = ''
  await loadGenome(selectedGenomeName.value, '')
}

const handleDefaultTrackToggle = async () => {
  if (!selectedGenomeName.value) return
  await loadGenome(selectedGenomeName.value, locusInput.value)
}

const handleAddCustomTrack = async () => {
  const name = customTrackForm.value.name.trim()
  const url = customTrackForm.value.url.trim()
  const format = customTrackForm.value.format.trim()

  if (!name || !url) {
    errorMessage.value = 'Track name and URL are required.'
    return
  }

  const newTrack = {
    name,
    type: customTrackForm.value.type,
    format: format || undefined,
    url,
    indexURL: customTrackForm.value.indexURL.trim() || undefined
  }

  try {
    errorMessage.value = ''
    customTracks.value.push(newTrack)

    if (browser.value && typeof browser.value.loadTrack === 'function') {
      await browser.value.loadTrack(newTrack)
    }

    customTrackForm.value = {
      name: '',
      type: 'annotation',
      format: 'gff3',
      url: '',
      indexURL: ''
    }
  } catch (error) {
    customTracks.value = customTracks.value.filter((track) => track !== newTrack)
    errorMessage.value = `Failed to add track: ${error?.message || String(error)}`
  }
}

const handleRemoveCustomTrack = async (index) => {
  const track = customTracks.value[index]
  if (!track) return

  customTracks.value.splice(index, 1)

  if (browser.value && typeof browser.value.removeTrack === 'function') {
    const runtimeTrack = browser.value.trackViews
      ?.map((view) => view.track)
      ?.find((item) => item?.name === track.name && item?.config?.url === track.url)
    if (runtimeTrack) {
      browser.value.removeTrack(runtimeTrack)
      return
    }
  }

  if (selectedGenomeName.value) {
    await loadGenome(selectedGenomeName.value, locusInput.value)
  }
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

.track-panel {
  border-top: 1px solid #e9ecef;
  padding-top: 16px;
}

.track-item {
  display: flex;
  align-items: center;
}

.custom-track-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.custom-track-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.track-name {
  max-width: 160px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 13px;
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
