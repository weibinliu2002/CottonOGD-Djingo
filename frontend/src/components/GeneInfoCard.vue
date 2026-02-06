<template>
  <el-card class="overview-card">
    <template #header>
      <div class="card-header">
        <h2>{{ t(title) }}</h2>
        <div class="gene-id-badge" v-if="geneData.IDs">
          <el-tag type="primary" size="large">{{ geneData.IDs }}</el-tag>
        </div>
      </div>
    </template>
    <div class="overview-content">
      <!-- 关键信息卡片 -->
      <div class="key-info-cards">
        <div class="info-card">
          <div class="info-icon">
            <i class="fas fa-chromosome"></i>
          </div>
          <div class="info-content">
            <div class="info-label">{{ t('chromosome') }}</div>
            <div class="info-value">{{ geneData.seqid || 'N/A' }}</div>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">
            <i class="fas fa-map-marker-alt"></i>
          </div>
          <div class="info-content">
            <div class="info-label">{{ t('location') }}</div>
            <div class="info-value">{{ geneData.gene_search_start }} - {{ geneData.gene_search_end }}</div>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">
            <i class="fas fa-arrows-alt-h"></i>
          </div>
          <div class="info-content">
            <div class="info-label">{{ t('strand') }}</div>
            <div class="info-value">{{ geneData.gene_search_strand || 'N/A' }}</div>
          </div>
        </div>
        <div class="info-card">
          <div class="info-icon">
            <i class="fas fa-transcript"></i>
          </div>
          <div class="info-content">
            <div class="info-label">{{ t('transcripts') }}</div>
            <div class="info-value">{{ geneData.mrna_transcripts?.length || 0 }}</div>
          </div>
        </div>
      </div>
      
      <!-- 基本信息表格 -->
      <!--<div class="basic-info-section" v-if="showBasicInfoTable">
        <h3 class="section-title">{{ t('basic_information') }}</h3>
        <el-table :data="basicInfoList" border class="basic-info-table">
          <el-table-column prop="label" label="Attribute" width="180" align="center" />
          <el-table-column prop="value" label="Value" />
        </el-table>
      </div>-->
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
  geneData: {
    type: Object,
    required: true
  },
  title: {
    type: String,
    default: 'gene_overview'
  },
  showBasicInfoTable: {
    type: Boolean,
    default: true
  }
})

const basicInfoList = computed(() => {
  if (!props.geneData) return []
  console.log(props.geneData)
  return [
    { label: 'gene_id', value: props.geneData.IDs },
    { label: 'chromosome', value: props.geneData.seqid || 'N/A' },
    { label: 'start_position', value: props.geneData.start || 'N/A' },
    { label: 'end_position', value: props.geneData.end || 'N/A' },
    { label: 'strand', value: props.geneData.strand || 'N/A' }
  ]
})
</script>

<style scoped>
.overview-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h2 {
  font-size: 18px;
  margin: 0;
}

.key-info-cards {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 20px;
}

.info-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background-color: #f8f9fa;
  padding: 15px;
  border-radius: 8px;
  min-width: 200px;
  flex: 1;
}

.info-icon {
  font-size: 24px;
  color: #3a6ea5;
}

.info-content {
  flex: 1;
}

.info-label {
  font-size: 14px;
  color: #6c757d;
  margin-bottom: 4px;
}

.info-value {
  font-size: 16px;
  font-weight: 500;
  color: #343a40;
}

.basic-info-section {
  margin-top: 20px;
}

.section-title {
  font-size: 16px;
  margin-bottom: 10px;
  color: #343a40;
}

.basic-info-table {
  width: 100%;
}
</style>