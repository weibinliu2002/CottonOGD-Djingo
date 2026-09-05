<template>
  <div class="container mt-4">
    <h2>Protein Structure Viewer Test</h2>
    
    <el-card class="mb-4">
      <template #header>Test Controls</template>
      <el-button @click="testDirect" type="primary">直接渲染 PDB 1CF7 (不调后端)</el-button>
      <el-button @click="testBackend" type="success">调后端 API 搜索</el-button>
    </el-card>

    <el-card v-if="showViewer">
      <template #header>3D Structure (PDB: {{ testPdbId }}, Chain: {{ testChain }})</template>
      <ProteinStructureViewer
        :pdb-id="testPdbId"
        :chain="testChain"
        :hit-info="testHitInfo"
      />
    </el-card>

    <el-card v-if="apiResponse" class="mt-4">
      <template #header>API Response</template>
      <pre style="white-space: pre-wrap; font-size: 12px;">{{ JSON.stringify(apiResponse, null, 2) }}</pre>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ProteinStructureViewer from '@/components/data-display/ProteinStructureViewer.vue'
import httpInstance from '@/utils/http.js'

const showViewer = ref(false)
const testPdbId = ref('1CF7')
const testChain = ref('4')
const apiResponse = ref<any>(null)
const testHitInfo = ref({
  pdb_id: '1CF7',
  chain: '4',
  description: 'Test PDB from API example',
  evalue: 999,
  identity: 0,
  bitscore: 0,
  cov_q: 0,
  cov_t: 0,
  rank: 1
})

const testDirect = () => {
  showViewer.value = false
  setTimeout(() => {
    testPdbId.value = '1CF7'
    testChain.value = '4'
    showViewer.value = true
  }, 100)
}

const testBackend = async () => {
  const seq = '>Ghir_A01G020590.3 protein\r\nMVTGSNSVQNHNHQEDGDQNRTKIGASRSWGTTVSGQSVSTSGSVGSPSSRSELAMATPASENTFLRLNHLDIHGDDAGSQGAVGSKKKKRGQRAVGGDKSGRGLRQFSMKVCEKVESKGRTTYNEVADELVAEFTDPGNNIASPDQRQYDEKNIRRRVYDALNVLMAMDIISKDKKEIQWKGLPRTSLSDIEDLKTERLGLRNRIEKKAAYLHELEEQFVGLQNLIQRNEQLYSSGNPLNGGVALPFILVQEKGAQ'

  const formData = new FormData()
  formData.append('sequence', seq)
  formData.append('method', 'rcsb_api')

  try {
    const response = await httpInstance.post('/CottonOGD_api/search_similar_structure/', formData)
    const data = response.data !== undefined ? response.data : response
    apiResponse.value = data

    if (data.top_hits && data.top_hits.length > 0) {
      const hit = data.top_hits[0]
      testPdbId.value = hit.pdb_id
      testChain.value = hit.chain
      testHitInfo.value = hit
      showViewer.value = false
      setTimeout(() => {
        showViewer.value = true
      }, 100)
    }
  } catch (e: any) {
    console.error('API error:', e)
    apiResponse.value = { error: e.message }
  }
}
</script>
