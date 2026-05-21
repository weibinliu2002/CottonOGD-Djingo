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

      <el-table :data="store.syntenyResult.reference_genes" style="width: 100%" stripe>
        <el-table-column prop="id" :label="t('id')" width="80" />
        <el-table-column :label="t('reference_position')" width="220">
          <template #default="scope">
            {{ scope.row.Ref_genome_chr }}:{{ scope.row.Ref_genome_start }}-{{ scope.row.Ref_genome_end }}
          </template>
        </el-table-column>
        <el-table-column :label="t('query_position')" width="220">
          <template #default="scope">
            {{ scope.row.Query_genome_chr }}:{{ scope.row.Query_genome_start }}-{{ scope.row.Query_genome_end }}
          </template>
        </el-table-column>
        <el-table-column prop="Variation_type" :label="t('variation_type')" width="140" />
        <el-table-column prop="son_type" :label="t('sub_type')" width="120" />
        <el-table-column prop="copygain" :label="t('copy_gain')" width="120">
          <template #default="scope">
            <el-tag :type="scope.row.copygain === 'copygain' ? 'success' : 'danger'" size="small">
              {{ scope.row.copygain }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="Parent_Variation" :label="t('parent_variation')" width="150" />
        <el-table-column prop="Ref_seq" :label="t('ref_seq')" width="100" />
        <el-table-column prop="Alt_seq" :label="t('alt_seq')" width="100" />
      </el-table>
    </el-card>

    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, inject } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search } from '@element-plus/icons-vue'
import { useEnrichmentStore } from '@/stores/enrichmentStore'
import { useGenomeSelector } from '@/composables/useGenomeBrowser'

const { t } = useI18n()
const store = useEnrichmentStore()
const showLoading = inject('showLoading') as (() => void) | undefined
const hideLoading = inject('hideLoading') as (() => void) | undefined

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
</style>
