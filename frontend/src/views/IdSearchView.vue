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
            <el-button type="default" @click="reset" class="ml-2">{{ t('reset') }}</el-button>
          </div>
          <div class="text-muted mt-1">{{ t('one_gene_id_per_line') }}</div>
        </el-form-item>
        
        <el-form-item :label="t('select_genome')">
          <el-tree-select
            v-model="geneSearchStore.selectedGenome"
            :data="genomeStore.genomeOptions"
            :props="{
              value: 'value',
              label: 'label',
              children: 'children'
            }"
            :placeholder="t('select_genome')"
            style="width: 100%"
            :loading="genomeStore.loading"
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
          <el-button type="primary" native-type="submit" :loading="geneSearchStore.loading">{{ t('search') }}</el-button>
        </el-form-item>
      </el-form>
      
      <!-- 错误提示 -->
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
import { ref, onMounted, inject } from 'vue';
import { useI18n } from 'vue-i18n';
import { useGenomeStore } from '@/stores/genome_info';
import { useGeneSearchStore } from '@/stores/geneSearch';
import { Upload } from '@element-plus/icons-vue';

const { t } = useI18n();

// 注入全局加载方法
const showLoading = inject('showLoading');
const hideLoading = inject('hideLoading');

// 获取 stores
const genomeStore = useGenomeStore();
const geneSearchStore = useGeneSearchStore();

const fileName = ref('');

// 组件挂载时加载基因组数据
onMounted(() => {
  genomeStore.fetchGenomes().then(() => {
    // 设置默认选择 G.hirsutumAD1_TM-1_HAU_v1.1
    const defaultGenome = 'G.hirsutumAD1_TM-1_HAU_v1.1';
    geneSearchStore.selectedGenome = [defaultGenome];
  });
});

const loadExample = () => {
  geneSearchStore.searchInput = `Ghir_A01G000040.1
Ghir_A01G000060
Ghir_A01G000290.1
Ghir_A01G000120.2`;
  geneSearchStore.clearError();
};

const reset = () => {
  geneSearchStore.clearState();
  fileName.value = '';
};

const handleFileSelect = (file) => {
  const selectedFile = file.raw;
  if (selectedFile) {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        geneSearchStore.searchInput = e.target.result.trim();
        fileName.value = selectedFile.name;
        console.log('Gene IDs loaded from file:', geneSearchStore.searchInput);
      } catch (error) {
        geneSearchStore.setError(t('file_read_failed') + ': ' + error.message);
        console.error('File read error:', error);
      }
    };
    reader.onerror = () => {
        geneSearchStore.setError('File read error');
        console.error('File reader error:', reader.error);
    };
    reader.readAsText(selectedFile);
  } else {
    fileName.value = '';
  }
};

const handleSubmit = async () => {
  console.log('handleSubmit triggered');
  showLoading();
  try {
    await geneSearchStore.performSearch(
      geneSearchStore.searchInput,
      geneSearchStore.selectedGenome
    );
  } catch (error) {
    // performSearch action 内部已经处理了错误状态，这里可以留空
    // 或者添加一些额外的、仅限此组件的UI反馈
    console.error('Search submission failed in component:', error);
  } finally {
    hideLoading();
  }
};
</script>

<style scoped>
.page-header {
  text-align: left;
  margin-bottom: 30px;
}

.page-title {
  font-size: 36px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.page-description {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  max-width: 800px;
  margin: 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 15px;
}
</style>
