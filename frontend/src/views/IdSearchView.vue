<template>
  <div class="container mt-4">
    <h1>Search by ID</h1>
    <el-card class="mt-4">
      <el-form @submit.prevent="handleSubmit" label-width="120px">
        <el-form-item label="Input Gene IDs">
          <el-input
            type="textarea"
            :rows="6"
            placeholder="请输入基因ID，一行一个"
            v-model="geneSearchStore.searchInput"
            ref="gene_ids"
          />
          <div class="mt-2">
            <el-button type="info" @click="loadExample">load example</el-button>
            <el-button type="default" @click="reset" class="ml-2">Reset</el-button>
          </div>
          <div class="text-muted mt-1">one gene ID per line</div>
        </el-form-item>
        
        <el-form-item label="Select Genome">
          <el-tree-select
            v-model="geneSearchStore.selectedGenome"
            :data="genomeStore.genomeOptions"
            :props="{
              value: 'value',
              label: 'label',
              children: 'children'
            }"
            placeholder="Select Genome"
            style="width: 100%"
            :loading="genomeStore.loading"
            multiple
          />
        </el-form-item>
        
        <el-form-item label="select file">
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
                <span>选择文件</span>
              </el-button>
              <span class="ml-2">{{ fileName || '未选择文件' }}</span>
            </template>
          </el-upload>
          <div class="text-muted mt-1">support .txt or .csv file</div>
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" native-type="submit" :loading="geneSearchStore.loading">Search</el-button>
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
import { useGenomeStore } from '@/stores/genome_info';
import { useGeneSearchStore } from '@/stores/geneSearch.js';
import { Upload } from '@element-plus/icons-vue';

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
        console.log('已从文件中读取基因ID:', geneSearchStore.searchInput);
      } catch (error) {
        geneSearchStore.setError('文件读取失败: ' + error.message);
        console.error('文件读取错误:', error);
      }
    };
    reader.onerror = () => {
      geneSearchStore.setError('文件读取错误');
      console.error('文件读取器错误:', reader.error);
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
