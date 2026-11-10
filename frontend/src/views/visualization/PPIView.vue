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

      <div v-if="inputMode === 'genes'" class="ppi-form">
        <el-form label-position="top" @submit.prevent="submitGeneIds">
          <el-form-item :label="t('select_genome')">
            <el-cascader
              v-model="selectedGenome"
              :options="genomeOptions"
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
          accept=".json,application/json"
          @change="handleFileChange"
        />
        <div class="ppi-upload__drop">
          <el-icon class="ppi-upload__icon"><UploadFilled /></el-icon>
          <p>{{ selectedFileName || t('ppi_upload_prompt') }}</p>
          <el-button @click="fileInputRef?.click()">{{ t('ppi_choose_json') }}</el-button>
        </div>
        <div class="ppi-upload__hint">
          <p>{{ t('ppi_json_format_hint') }}</p>
          <pre>{{ exampleJson }}</pre>
        </div>
      </div>
    </el-card>

    <el-card class="ppi-card ppi-results" shadow="never">
      <template #header><span>{{ t('ppi_network_title') }}</span></template>
      <PpiNetworkViewer v-if="network.elements.length" :elements="network.elements" />
      <el-empty v-else :description="t('ppi_network_empty')" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { UploadFilled } from '@element-plus/icons-vue'
import PpiNetworkViewer from '@/components/data-display/PpiNetworkViewer.vue'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'
import { getStringPpiNetwork } from '@/api'
import { parsePpiNetwork, type PpiNetwork } from '@/utils/ppiNetwork'

type InputMode = 'genes' | 'file'

const { t } = useI18n()
const {
  selectedGenome,
  genomeOptions,
  genomeLoading,
  cascaderProps,
  ensureGenomesLoaded,
  pickDefaultGenome,
  setSelectedGenome,
} = useGenomeSelector()

const inputMode = ref<InputMode>('genes')
const geneIdsText = ref('')
const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFileName = ref('')
const loading = ref(false)
const errorMessage = ref('')
const network = ref<PpiNetwork>({ elements: [] })
const selectedGenomeName = computed(
  () => selectedGenome.value[selectedGenome.value.length - 1] || '',
)

const exampleJson = `{
  "elements": {
    "nodes": [
      { "data": { "id": "geneA", "label": "Gene A" } },
      { "data": { "id": "geneB", "label": "Gene B" } }
    ],
    "edges": [
      { "data": { "id": "geneA-geneB", "source": "geneA", "target": "geneB", "score": 850 } }
    ]
  }
}`

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
  const geneIds = [...new Set(geneIdsText.value.split(/[\s,;]+/).map((id) => id.trim()).filter(Boolean))]
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
    network.value = await getStringPpiNetwork({
      gene_ids: geneIds,
      genome_id: selectedGenomeName.value,
    })
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

  errorMessage.value = ''
  selectedFileName.value = file.name
  try {
    network.value = parsePpiNetwork(JSON.parse(await file.text()))
  } catch (error) {
    errorMessage.value = getErrorMessage(error)
  } finally {
    input.value = ''
  }
}

onMounted(async () => {
  await ensureGenomesLoaded()
  if (genomeOptions.value.length) {
    setSelectedGenome(pickDefaultGenome())
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
