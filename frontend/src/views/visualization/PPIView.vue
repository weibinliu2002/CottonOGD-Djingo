<template>
  <div class="ppi-page">
    <header class="ppi-page__header">
      <h1>{{ t('ppi') }}</h1>
      <p>{{ t('ppi_description') }}</p>
    </header>

    <el-card class="ppi-card" shadow="never">
      <template #header>
        <div class="ppi-card__header">
          <span>{{ t('ppi_input_title') }}</span>
          <el-radio-group v-model="inputMode" size="small">
            <el-radio-button value="genes">{{ t('ppi_gene_input') }}</el-radio-button>
            <el-radio-button value="file">{{ t('ppi_upload_input') }}</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <el-alert
        v-if="errorMessage"
        class="ppi-alert"
        type="error"
        :title="errorMessage"
        show-icon
        :closable="true"
        @close="errorMessage = ''"
      />
      <el-alert
        v-if="infoMessage"
        class="ppi-alert"
        type="warning"
        :title="infoMessage"
        show-icon
        :closable="true"
        @close="infoMessage = ''"
      />

      <div v-if="inputMode === 'genes'" class="ppi-form">
        <el-form label-position="top" @submit.prevent="submitGeneIds">
          <el-form-item :label="t('select_genome')">
            <el-cascader
              v-model="selectedGenome"
              :options="ppiGenomeOptions"
              :props="cascaderProps"
              :placeholder="t('select_genome')"
              :loading="genomeLoading"
              clearable
              filterable
              class="ppi-form__genome"
            />
          </el-form-item>
          <el-form-item :label="t('ppi_gene_ids')">
            <el-input
              v-model="geneIdsText"
              type="textarea"
              :rows="5"
              :placeholder="t('ppi_gene_ids_placeholder')"
              resize="vertical"
            />
            <div class="ppi-form__hint">{{ t('ppi_gene_ids_hint') }}</div>
          </el-form-item>
          <el-button type="primary" :loading="loading" @click="submitGeneIds">
            {{ t('ppi_build_network') }}
          </el-button>
        </el-form>
      </div>

      <div v-else class="ppi-upload">
        <input
          ref="fileInputRef"
          class="ppi-upload__input"
          type="file"
          accept=".json,.cyjs,.graphml,.xgmml,.xml,.sif,.txt,.csv,.tsv,.xls,.xlsx,application/json,text/*,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel,*/*"
          @change="handleFileChange"
        />
        <div class="ppi-upload__drop" @dragover.prevent @drop.prevent="handleFileDrop">
          <el-icon class="ppi-upload__icon"><UploadFilled /></el-icon>
          <p>{{ selectedFileName || t('ppi_upload_prompt') }}</p>
          <el-button @click="fileInputRef?.click()">{{ t('ppi_choose_file') }}</el-button>
        </div>
        <el-form-item class="ppi-upload__format" :label="t('ppi_upload_format')">
          <el-select v-model="uploadFormat" class="ppi-upload__format-select">
            <el-option value="auto" :label="t('ppi_format_auto')" />
            <el-option value="cytoscape" :label="t('ppi_format_cytoscape')" />
            <el-option value="table" :label="t('ppi_format_table')" />
          </el-select>
          <div class="ppi-form__hint">{{ t('ppi_format_override_hint') }}</div>
        </el-form-item>
        <div class="ppi-upload__hint">
          <p>{{ t('ppi_json_format_hint') }}</p>
          <p>{{ t('ppi_table_format_hint') }}</p>
          <pre>{{ exampleTable }}</pre>
        </div>
      </div>
    </el-card>

    <el-card class="ppi-card ppi-results" shadow="never">
      <template #header
        ><span>{{ t('ppi_network_title') }}</span></template
      >
      <PpiNetworkViewer v-if="network.elements.length" :elements="network.elements" />
      <el-empty v-else :description="t('ppi_network_empty')" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { UploadFilled } from '@element-plus/icons-vue'
import PpiNetworkViewer from '@/components/data-display/PpiNetworkViewer.vue'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { getStringPpiNetwork } from '@/api'
import { parsePpiUpload, type PpiNetwork, type PpiUploadFormat } from '@/utils/ppiNetwork'

type InputMode = 'genes' | 'file'

const { t } = useI18n()
const { genomeOptions, genomeLoading, cascaderProps, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()

const inputMode = ref<InputMode>('genes')
const selectedGenome = ref<string[]>([])
const uploadFormat = ref<PpiUploadFormat>('auto')
const geneIdsText = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFile = ref<File | null>(null)
const selectedFileName = ref('')
const loading = ref(false)
const errorMessage = ref('')
const infoMessage = ref('')
const network = ref<PpiNetwork>({ elements: [] })
const ppiGenomeOptions = computed(() =>
  genomeOptions.value
    .map((group) => ({
      ...group,
      children: (group.children || []).filter(
        (genome) =>
          genome.value.trim() !== '' &&
          genome.value.toLowerCase() !== 'undefined' &&
          genome.label.trim() !== '' &&
          genome.label.toLowerCase() !== 'undefined',
      ),
    }))
    .filter(
      (group) =>
        group.value.trim() !== '' &&
        group.value.toLowerCase() !== 'undefined' &&
        group.label.trim() !== '' &&
        group.label.toLowerCase() !== 'undefined' &&
        (group.children?.length || 0) > 0,
    ),
)
const availableGenomes = computed(() =>
  ppiGenomeOptions.value.flatMap((group) => group.children || []).map((genome) => genome.value),
)
const selectedGenomeName = computed(() => selectedGenome.value?.[selectedGenome.value.length - 1] || '')

const exampleTable = `source,target,score
geneA,geneB,850
geneB,geneC,720`
let uploadParseRequest = 0

function getErrorMessage(error: unknown): string {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = error.response
    if (typeof response === 'object' && response !== null && 'data' in response) {
      const data = response.data
      if (typeof data === 'object' && data !== null) {
        if ('message' in data && typeof data.message === 'string') return data.message
        if ('error' in data && typeof data.error === 'string') return data.error
      }
    }
  }
  if (error instanceof Error && error.message) return error.message
  return t('ppi_request_failed')
}

async function submitGeneIds(): Promise<void> {
  errorMessage.value = ''
  infoMessage.value = ''
  const geneIds = [
    ...new Set(
      geneIdsText.value
        .split(/[\s,;]+/)
        .map((id) => id.trim())
        .filter(Boolean),
    ),
  ]
  if (!geneIds.length) {
    errorMessage.value = t('ppi_enter_gene_ids')
    return
  }
  if (!selectedGenomeName.value) {
    errorMessage.value = t('select_genome_first')
    return
  }

  loading.value = true
  try {
    const result = await getStringPpiNetwork({
      gene_ids: geneIds,
      genome_id: selectedGenomeName.value,
    })
    network.value = result.network
    infoMessage.value = result.message
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    loading.value = false
  }
}

async function handleFileChange(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return

  await loadNetworkFile(file)
  input.value = ''
}

async function handleFileDrop(event: DragEvent): Promise<void> {
  const file = event.dataTransfer?.files[0]
  if (file) await loadNetworkFile(file)
}

async function loadNetworkFile(file: File): Promise<void> {
  selectedFile.value = file
  errorMessage.value = ''
  infoMessage.value = ''
  selectedFileName.value = file.name
  network.value = { elements: [] }
  const requestId = ++uploadParseRequest
  try {
    const parsedNetwork = await parsePpiUpload(file, uploadFormat.value)
    if (requestId === uploadParseRequest) network.value = parsedNetwork
  } catch (error) {
    if (requestId === uploadParseRequest) errorMessage.value = getErrorMessage(error)
  }
}

watch(uploadFormat, () => {
  if (selectedFile.value) void loadNetworkFile(selectedFile.value)
})

onMounted(async () => {
  await ensureGenomesLoaded()
  const fallbackGenome = availableGenomes.value[0]
  if (fallbackGenome) {
    const preferredGenome = pickDefaultGenome()
    const genomeName = availableGenomes.value.includes(preferredGenome) ? preferredGenome : fallbackGenome
    const group = ppiGenomeOptions.value.find((option) =>
      option.children?.some((genome) => genome.value === genomeName),
    )
    if (group) selectedGenome.value = [group.value, genomeName]
  }
})
</script>

<style scoped>
.ppi-page {
  max-width: 1440px;
  margin: 0 auto;
  padding: 1.5rem;
}

.ppi-page__header h1 {
  margin: 0 0 0.35rem;
  color: #315f85;
  font-size: 1.6rem;
}

.ppi-page__header p {
  margin: 0 0 1.25rem;
  color: #667788;
}

.ppi-card {
  margin-bottom: 1.25rem;
  border: 1px solid #e3e9ee;
  border-radius: 10px;
}

.ppi-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  font-weight: 600;
}

.ppi-alert {
  margin-bottom: 1rem;
}

.ppi-form__genome {
  width: min(100%, 520px);
}

.ppi-form__hint {
  margin-top: 0.4rem;
  color: #718096;
  font-size: 0.85rem;
}

.ppi-upload__input {
  display: none;
}

.ppi-upload__drop {
  display: flex;
  min-height: 180px;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  border: 1px dashed #9aafbf;
  border-radius: 8px;
  background: #f8fbfd;
  color: #536273;
}

.ppi-upload__drop p {
  margin: 0;
}

.ppi-upload__icon {
  color: #4a87ad;
  font-size: 2rem;
}

.ppi-upload__hint {
  margin-top: 1rem;
  color: #64748b;
  font-size: 0.85rem;
}

.ppi-upload__format {
  margin: 1rem 0 0;
}

.ppi-upload__format-select {
  width: min(100%, 360px);
}

.ppi-upload__hint p {
  margin-bottom: 0.4rem;
}

.ppi-upload__hint pre {
  max-height: 220px;
  overflow: auto;
  padding: 0.75rem;
  border-radius: 6px;
  background: #f5f7f9;
  color: #34495e;
  font-size: 0.78rem;
}

.ppi-results :deep(.el-card__body) {
  padding: 1rem;
}

@media (max-width: 640px) {
  .ppi-page {
    padding: 1rem;
  }

  .ppi-card__header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
