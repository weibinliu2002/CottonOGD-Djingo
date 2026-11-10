<script setup lang="ts">
/**
 * 单个 Orthogroup 详情页（阶段 5.2）。
 *
 * 路由：/tools/orthogroup/:og_code  —— 例如 /tools/orthogroup/OG0000001
 * 从 OG 浏览列表、按基因查、主页检索均可深链进入。
 *
 * 展示分区（各模块独立 loading / error，互不阻塞）：
 *  1. OG 元信息（species_count / gene_count / 是否单拷贝）
 *  2. 成员基因表（分页，可跳基因详情；来自 orthogroup_detail）
 *  3. MSA（多序列比对，FASTA 文本；后端接口用户后续补齐，未就绪静默降级）
 *  4. Tree（基因树 newick，复用 OrthogroupTreeViewer；后端无 treefile 时友好提示）
 *  5. WGS（后端接口用户后续补齐）
 *  6. 串联重复（tandem，后端接口用户后续补齐）
 *
 * 数据源：全部走真实后端 /CottonOGD_api/orthofinder/，无 mock。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search, Download } from '@element-plus/icons-vue'
import OrthogroupTreeViewer from '@/components/data-display/OrthogroupTreeViewer.vue'
import {
  getOrthogroupDetailV2,
  getOrthogroupSequence,
  getOrthogroupTree,
  getOrthogroupMsa,
  getOrthogroupWgs,
  getOrthogroupTandem,
  type OrthologOrthogroup,
  type OrthologSpeciesMember,
} from '@/api/index'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const ogCode = computed(() => (route.params.og_code as string) || '')

// ============ OG 元信息 + 成员 ============
const detailLoading = ref(false)
const detailData = ref<OrthologOrthogroup | null>(null)
const detailError = ref('')
const detailGeneFilter = ref('')

const filteredMembers = computed<OrthologSpeciesMember[]>(() => {
  if (!detailData.value) return []
  const kw = detailGeneFilter.value.trim().toLowerCase()
  const members = detailData.value.species_members || []
  if (!kw) return members
  return members
    .map((m) => ({
      ...m,
      genes: m.genes.filter(
        (g) =>
          (g.ortho_gene || '').toLowerCase().includes(kw) ||
          (g.genemaster_geneid || '').toLowerCase().includes(kw),
      ),
    }))
    .filter((m) => m.genes.length > 0)
})

function speciesName(member: OrthologSpeciesMember): string {
  return member.display_name || member.species
}
function openGene(genemasterGeneid: string | null): void {
  if (!genemasterGeneid) return
  router.push({ name: 'GenomeDetail', params: { key: genemasterGeneid } })
}

// ============ MSA ============
const msaLoading = ref(false)
const msaText = ref('')
const msaError = ref('')

// ============ Tree ============
const treeText = ref('')
const treeError = ref('')

// ============ WGS ============
const wgsLoading = ref(false)
const wgsText = ref('')
const wgsError = ref('')

// ============ 串联重复 ============
const tandemLoading = ref(false)
const tandemData = ref<Record<string, { geneid: string; n: number }[]> | null>(null)
const tandemError = ref('')
const tandemSpecies = computed(() => (tandemData.value ? Object.keys(tandemData.value) : []))

// ============ 加载逻辑 ============
async function loadDetail(): Promise<void> {
  detailLoading.value = true
  detailError.value = ''
  detailData.value = null
  detailGeneFilter.value = ''
  try {
    detailData.value = await getOrthogroupDetailV2(ogCode.value)
    if (!detailData.value) detailError.value = t('ortholog_not_found')
  } catch {
    detailError.value = t('ortholog_not_found')
  } finally {
    detailLoading.value = false
  }
}

async function loadMsa(): Promise<void> {
  msaLoading.value = true
  msaError.value = ''
  msaText.value = ''
  try {
    const txt = await getOrthogroupMsa(ogCode.value)
    if (!txt) msaError.value = t('og_module_not_ready')
    else msaText.value = txt
  } catch {
    msaError.value = t('og_module_not_ready')
  } finally {
    msaLoading.value = false
  }
}

async function loadTree(): Promise<void> {
  treeError.value = ''
  try {
    const txt = await getOrthogroupTree(ogCode.value)
    if (!txt || txt.trim().startsWith('{"error"')) {
      treeError.value = t('og_tree_not_found')
      treeText.value = ''
    } else {
      treeText.value = txt.trim()
    }
  } catch {
    treeError.value = t('og_tree_not_found')
    treeText.value = ''
  }
}

async function loadWgs(): Promise<void> {
  wgsLoading.value = true
  wgsError.value = ''
  wgsText.value = ''
  try {
    const txt = await getOrthogroupWgs(ogCode.value)
    if (!txt) wgsError.value = t('og_module_not_ready')
    else wgsText.value = txt
  } catch {
    wgsError.value = t('og_module_not_ready')
  } finally {
    wgsLoading.value = false
  }
}

async function loadTandem(): Promise<void> {
  tandemLoading.value = true
  tandemError.value = ''
  tandemData.value = null
  try {
    const data = await getOrthogroupTandem(ogCode.value)
    if (!data || Object.keys(data).length === 0) tandemError.value = t('og_module_not_ready')
    else tandemData.value = data
  } catch {
    tandemError.value = t('og_module_not_ready')
  } finally {
    tandemLoading.value = false
  }
}

function copyText(text: string): void {
  if (!text) return
  navigator.clipboard?.writeText(text).catch(() => {})
}

function backToList(): void {
  router.push({ name: 'Orthogroup' })
}

onMounted(async () => {
  if (!ogCode.value) {
    detailError.value = t('ortholog_not_found')
    return
  }
  await loadDetail()
  // 列表/明细就绪后再并行拉取各分析模块（各自独立失败不影响整体）
  await Promise.allSettled([loadMsa(), loadTree(), loadWgs(), loadTandem()])
})

watch(ogCode, async () => {
  treeText.value = ''
  await loadDetail()
  await Promise.allSettled([loadMsa(), loadTree(), loadWgs(), loadTandem()])
})
</script>

<template>
  <div class="container og-detail">
    <div class="og-detail__nav">
      <el-button link type="primary" size="small" @click="backToList">
        ← {{ t('orthogroup') }}
      </el-button>
      <span class="og-detail__code">{{ ogCode }}</span>
    </div>

    <!-- 元信息 + 成员 -->
    <el-card class="og-card" shadow="never">
      <template #header>
        <div class="og-card__head">
          <span>{{ t('og_overview') }}</span>
          <el-button
            v-if="detailData"
            size="small"
            :icon="Download"
            @click="copyText(ogCode)"
          >{{ t('copy_og_code') }}</el-button>
        </div>
      </template>
      <div v-loading="detailLoading">
        <el-alert v-if="detailError" type="warning" :title="detailError" show-icon :closable="false" />
        <template v-else-if="detailData">
          <el-descriptions :column="3" border class="mb-4">
            <el-descriptions-item :label="t('og_code')">{{ detailData.og_code }}</el-descriptions-item>
            <el-descriptions-item :label="t('species_count')">{{ detailData.species_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('gene_count')">{{ detailData.gene_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('homology_single_copy')">
              {{ detailData.is_single_copy ? t('yes') : t('no') }}
            </el-descriptions-item>
            <el-descriptions-item :label="t('homology_annotation')">
              {{ detailData.annotation || '-' }}
            </el-descriptions-item>
          </el-descriptions>

          <div class="browse-filters mb-4">
            <el-input
              v-model="detailGeneFilter"
              class="browse-filters__ann"
              :placeholder="t('detail_gene_filter_placeholder')"
              clearable
              size="default"
            />
            <span class="og-og__meta">{{ t('ortholog_genes') }} · {{ filteredMembers.length }} / {{ (detailData.species_members || []).length }} {{ t('species') }}</span>
          </div>

          <el-table :data="filteredMembers" stripe border size="small">
            <el-table-column :label="t('ortholog_species')" min-width="220">
              <template #default="scope">{{ speciesName(scope.row) }}</template>
            </el-table-column>
            <el-table-column :label="t('n_genes')" prop="n" width="100" align="center" />
            <el-table-column :label="t('ortholog_genes')" min-width="420">
              <template #default="scope">
                <span v-for="(g, idx) in scope.row.genes" :key="g.ortho_gene" class="ortholog-gene">
                  <a
                    v-if="g.genemaster_geneid"
                    class="ortholog-gene__link"
                    @click="openGene(g.genemaster_geneid)"
                  >{{ g.genemaster_geneid }}</a>
                  <span v-else class="ortholog-gene__plain">{{ g.ortho_gene }}</span>
                  <span v-if="idx !== scope.row.genes.length - 1" class="ortholog-gene__sep">, </span>
                </span>
              </template>
            </el-table-column>
          </el-table>
        </template>
        <el-empty v-else :description="t('no_data')" />
      </div>
    </el-card>

    <!-- MSA -->
    <el-card class="og-card" shadow="never">
      <template #header><span>{{ t('og_msa') }}</span></template>
      <div v-loading="msaLoading">
        <el-alert v-if="msaError" type="info" :title="msaError" show-icon :closable="false" />
        <pre v-else-if="msaText" class="og-fasta">{{ msaText }}</pre>
        <el-empty v-else :description="t('no_data')" />
      </div>
    </el-card>

    <!-- Tree -->
    <el-card class="og-card" shadow="never">
      <template #header><span>{{ t('og_tree') }}</span></template>
      <el-alert v-if="treeError" type="info" :title="treeError" show-icon :closable="false" />
      <OrthogroupTreeViewer v-else :newick="treeText" />
    </el-card>

    <!-- WGS -->
    <el-card class="og-card" shadow="never">
      <template #header><span>{{ t('og_wgs') }}</span></template>
      <div v-loading="wgsLoading">
        <el-alert v-if="wgsError" type="info" :title="wgsError" show-icon :closable="false" />
        <pre v-else-if="wgsText" class="og-fasta">{{ wgsText }}</pre>
        <el-empty v-else :description="t('no_data')" />
      </div>
    </el-card>

    <!-- 串联重复 -->
    <el-card class="og-card" shadow="never">
      <template #header><span>{{ t('og_tandem') }}</span></template>
      <div v-loading="tandemLoading">
        <el-alert v-if="tandemError" type="info" :title="tandemError" show-icon :closable="false" />
        <template v-else-if="tandemData">
          <el-collapse>
            <el-collapse-item v-for="sp in tandemSpecies" :key="sp" :title="sp" :name="sp">
              <el-table :data="tandemData[sp]" stripe border size="small">
                <el-table-column :label="t('ortholog_genes')" prop="geneid" min-width="220" />
                <el-table-column :label="t('n_genes')" prop="n" width="120" align="center" />
              </el-table>
            </el-collapse-item>
          </el-collapse>
        </template>
        <el-empty v-else :description="t('no_data')" />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.og-detail {
  max-width: 1280px;
  margin: 0 auto;
  padding-bottom: 2rem;
}
.og-detail__nav {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}
.og-detail__code {
  font-weight: 600;
  font-size: 1.1rem;
  color: #3a6ea5;
}
.og-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  margin-bottom: 1.25rem;
}
.og-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
.og-fasta {
  max-height: 420px;
  overflow: auto;
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 8px;
  padding: 0.75rem;
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.82rem;
  white-space: pre;
  color: #495057;
}
.browse-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.browse-filters__ann {
  width: 260px;
}
.og-og__meta {
  color: #6c757d;
  font-size: 0.85rem;
}
.ortholog-gene {
  font-size: 0.9rem;
}
.ortholog-gene__link {
  color: #3a6ea5;
  cursor: pointer;
  text-decoration: none;
}
.ortholog-gene__link:hover {
  text-decoration: underline;
}
.ortholog-gene__plain {
  color: #495057;
}
.ortholog-gene__sep {
  color: #adb5bd;
}
.mb-4 {
  margin-bottom: 1.5rem;
}
</style>
