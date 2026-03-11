<template>
  <div class="container mt-4">
    <h1>{{ t('search_by_id') }}</h1>
    <el-card class="mt-4">
      <el-form @submit.prevent="handleSubmit" label-width="120px">
        <el-form-item :label="t('input_gene_ids')">
          <el-input
            type="textarea"
            :rows="6"
            :placeholder="t('please_enter_gene_ids_one_per_line')"
            v-model="geneSearchStore.searchInput"
            ref="gene_ids"
          />
          <div class="mt-2">
            <el-button type="info" @click="loadExample">{{ t('load_example') }}</el-button>
            <el-button type="default" @click="reset" class="ml-2 reset-action-btn">{{ t('reset') }}</el-button>
          </div>
          <div class="text-muted mt-1">{{ t('one_gene_id_per_line') }}</div>
        </el-form-item>

        <el-form-item :label="t('select_genome')">
          <el-tree-select
            v-model="geneSearchStore.selectedGenome"
            :data="genomeOptions"
            :props="{
              value: 'value',
              label: 'label',
              children: 'children'
            }"
            :placeholder="t('select_genome')"
            style="width: 100%"
            :loading="genomeLoading"
            multiple
          />
        </el-form-item>

        <el-form-item :label="t('select_file')">
          <el-upload
            class="upload-demo"
            action="#"
            :auto-upload="false"
            :on-change="handleFileSelect"
            :show-file-list="false"
            accept=".txt,.csv,.xls,.xlsx"
          >
            <template #default>
              <el-button type="primary">
                <el-icon><Upload /></el-icon>
                <span>{{ t('select_file') }}</span>
              </el-button>
              <span class="ml-2">{{ fileName || t('no_file_selected') }}</span>
            </template>
          </el-upload>
          <div class="text-muted mt-1">{{ t('support_txt_or_csv_file') }}</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="geneSearchStore.isLoading">{{ t('search') }}</el-button>
        </el-form-item>
      </el-form>

      <el-alert
        v-if="geneSearchStore.error"
        :title="geneSearchStore.error"
        type="error"
        show-icon
        class="mt-3"
        @close="geneSearchStore.clearError()"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'
import { useGeneSearchStore } from '@/stores/geneSearch'
import { Upload } from '@element-plus/icons-vue'

const { t } = useI18n()

const showLoading = inject('showLoading')
const hideLoading = inject('hideLoading')

const { genomeOptions, genomeLoading, ensureGenomesLoaded, pickDefaultGenome } = useGenomeSelector()
const geneSearchStore = useGeneSearchStore()

const fileName = ref('')

onMounted(async () => {
  await ensureGenomesLoaded()
  const defaultGenome = pickDefaultGenome()
  if (defaultGenome) {
    geneSearchStore.selectedGenome = [defaultGenome]
  }
})

const loadExample = () => {
  geneSearchStore.searchInput = `Ghir_A01G000040.1
Ghir_A01G000060
Ghir_A01G000290.1
Ghir_A01G000120.2`
  geneSearchStore.clearError()
}

const reset = () => {
  geneSearchStore.clearState()
  fileName.value = ''
}

const handleFileSelect = (file) => {
  const selectedFile = file.raw
  if (selectedFile) {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        geneSearchStore.searchInput = e.target.result.trim()
        fileName.value = selectedFile.name
      } catch (error) {
        geneSearchStore.setError(`${t('file_read_failed')}: ${error.message}`)
      }
    }
    reader.onerror = () => {
      geneSearchStore.setError('File read error')
    }
    reader.readAsText(selectedFile)
  } else {
    fileName.value = ''
  }
}

const handleSubmit = async () => {
  showLoading?.()
  try {
    await geneSearchStore.performSearch(geneSearchStore.searchInput, geneSearchStore.selectedGenome)
  } catch (error) {
    console.error('Search submission failed in component:', error)
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
</style>
