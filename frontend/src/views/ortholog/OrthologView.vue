<script setup lang="ts">
/**
 * 同源分析 / Orthogroup 统一查询页（阶段 5.1，合并 HomologyView + OrthologView）
 *
 * 对标 SoyOmics 的 Homology 模块，单页承载两类入口：
 *  - Tab「浏览 Orthogroup」：左侧基因组复选框 + 顶部 OG id / 注释筛选 + 单拷贝开关，
 *    默认展示若干 OG（后端 orthogroups_by_species：未选基因组时按 any + 全部基因组取默认列表）；
 *    点击 OG 行 → 抽屉展示该簇跨物种成员（行=物种，列=成员基因，可链接跳基因详情）。
 *  - Tab「按基因查」：保留原 OrthologView 的基因→OG 跨物种检索（不丢失已有功能）。
 *
 * 数据源：全部走真实后端 /CottonOGD_api/orthofinder/，无 mock。
 *
 * ⚠️ 后端约定说明：orthogroup 的列表与明细目前**不返回 annotation 字段**。
 * 因此「注释筛选」在列表层退化为对 og_code 的匹配（后端补齐 annotation 后自动切换为按注释匹配）；
 * 真正的「按成员基因/注释筛选」放在 OG 明细抽屉内（成员基因 id 在明细中可用）。
 */
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import {
  getOrthologByGene,
  getOrthogroupDetailV2,
  getOrthogroupsBySpecies,
  getOrthologMeta,
  type OrthologOrthogroup,
  type OrthologSpeciesMember,
  type OrthologSpeciesMeta,
} from '@/api/index'

const { t } = useI18n()
const router = useRouter()

const activeTab = ref<'browse' | 'gene'>('browse')

// ============ 物种元数据（左侧复选框 + 默认列表用） ============
const metaList = ref<OrthologSpeciesMeta[]>([])
const allSpeciesNames = computed(() => metaList.value.map((m) => m.name))
const speciesOptions = computed(() =>
  metaList.value.map((m) => ({
    name: m.name,
    label: m.alias || m.Cotton_Species || m.name,
  })),
)
const selectedSpecies = ref<string[]>([])

/** 选中「全选」= 未勾选任何基因组 → 默认列表（any + 全部） */
const isAllSelected = computed(
  () => selectedSpecies.value.length === allSpeciesNames.value.length,
)
function toggleSelectAll(): void {
  selectedSpecies.value =
    selectedSpecies.value.length === allSpeciesNames.value.length
      ? []
      : [...allSpeciesNames.value]
}

// ============ 浏览 Tab：筛选 + 列表 ============
const ogIdFilter = ref('')
const annotationFilter = ref('')
const singleCopyOnly = ref(false)
const ogLimit = ref(20)
const ogOffset = ref(0)
const ogList = ref<OrthologOrthogroup[]>([])
const ogTotal = ref(0)
const ogLoading = ref(false)
const ogError = ref('')
const sortProp = ref('')
const sortOrder = ref<'ascending' | 'descending' | null>(null)

/** 真正发给后端的物种参数：未选则传全部（默认列表），有选则直接用 */
function resolveQuerySpecies(): string[] {
  return selectedSpecies.value.length ? selectedSpecies.value : allSpeciesNames.value
}
/** 未选任何基因组时，mode 用 any（默认列表）；有选时按 speciesMode */
const speciesMode = ref<'all' | 'any'>('all')
function resolveQueryMode(): 'all' | 'any' {
  return selectedSpecies.value.length ? speciesMode.value : 'any'
}

/** 客户端筛选 + 排序（应用于已加载的页面数据） */
const filteredOgs = computed<OrthologOrthogroup[]>(() => {
  const idKw = ogIdFilter.value.trim().toLowerCase()
  const annKw = annotationFilter.value.trim().toLowerCase()
  let list = ogList.value
  if (singleCopyOnly.value) list = list.filter((o) => o.is_single_copy)
  if (idKw) list = list.filter((o) => o.og_code.toLowerCase().includes(idKw))
  // 注释字段后端暂未提供，退化为对 og_code 匹配；补齐 annotation 后自动改为按注释匹配
  if (annKw) {
    list = list.filter(
      (o) =>
        (o.annotation ?? o.og_code).toLowerCase().includes(annKw),
    )
  }
  if (sortProp.value && sortOrder.value) {
    const dir = sortOrder.value === 'ascending' ? 1 : -1
    const prop = sortProp.value as keyof OrthologOrthogroup
    list = [...list].sort((a, b) => {
      const va = a[prop] as number | string
      const vb = b[prop] as number | string
      if (va === vb) return 0
      return (va > vb ? 1 : -1) * dir
    })
  }
  return list
})

const ogHasMore = computed(() => ogList.value.length < ogTotal.value)

/** 拉取 OG 列表：reset=true 时回到首页 */
async function loadOgs(reset = true): Promise<void> {
  ogLoading.value = true
  ogError.value = ''
  if (reset) {
    ogOffset.value = 0
    ogList.value = []
  }
  try {
    const res = await getOrthogroupsBySpecies({
      species: resolveQuerySpecies(),
      mode: resolveQueryMode(),
      limit: ogLimit.value,
      offset: ogOffset.value,
    })
    ogTotal.value = res.total ?? 0
    const items = res.orthogroups ?? []
    ogList.value = reset ? items : [...ogList.value, ...items]
    if (!res.found && ogList.value.length === 0) {
      ogError.value = t('ortholog_not_found')
    }
  } catch {
    ogError.value = t('ortholog_not_found')
  } finally {
    ogLoading.value = false
  }
}

function loadMore(): void {
  if (!ogHasMore.value || ogLoading.value) return
  ogOffset.value += ogLimit.value
  loadOgs(false)
}

function handleSortChange(payload: { prop: string | null; order: 'ascending' | 'descending' | null }): void {
  sortProp.value = payload?.prop ?? ''
  sortOrder.value = payload?.order ?? null
}

watch(selectedSpecies, () => loadOgs(true), { deep: true })
watch(speciesMode, () => {
  if (selectedSpecies.value.length) loadOgs(true)
})

// ============ 明细抽屉 ============
const drawerVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<OrthologOrthogroup | null>(null)
const detailGeneFilter = ref('')

const filteredMembers = computed<OrthologSpeciesMember[]>(() => {
  if (!detailData.value) return []
  const kw = detailGeneFilter.value.trim().toLowerCase()
  if (!kw) return detailData.value.species_members
  return detailData.value.species_members
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

async function openDetail(ogCode: string): Promise<void> {
  drawerVisible.value = true
  detailLoading.value = true
  detailData.value = null
  detailGeneFilter.value = ''
  try {
    detailData.value = await getOrthogroupDetailV2(ogCode)
  } finally {
    detailLoading.value = false
  }
}

function speciesName(member: OrthologSpeciesMember): string {
  return member.display_name || member.species
}

/** genemaster_geneid 有值则跳基因详情页 */
function openGene(genemasterGeneid: string | null): void {
  if (!genemasterGeneid) return
  router.push({ name: 'GenomeDetail', params: { key: genemasterGeneid } })
}

// ============ Tab「按基因查」（保留原 OrthologView 功能） ============
const geneInput = ref('')
const geneLoading = ref(false)
const geneError = ref('')
const orthoResult = ref<{ query_gene: string; found: boolean; orthogroups: OrthologOrthogroup[] } | null>(null)

function relationLabel(type: string): string {
  const map: Record<string, string> = {
    one_to_one: t('one_to_one'),
    one_to_many: t('one_to_many'),
    many_to_one: t('many_to_one'),
    many_to_many: t('many_to_many'),
  }
  return map[type] ?? type
}

async function searchByGene(): Promise<void> {
  const geneid = geneInput.value.trim()
  if (!geneid) {
    geneError.value = t('ortholog_gene_placeholder')
    return
  }
  geneLoading.value = true
  geneError.value = ''
  orthoResult.value = null
  try {
    const res = await getOrthologByGene(geneid)
    orthoResult.value = res
    if (!res.found) geneError.value = t('ortholog_not_found')
  } catch {
    geneError.value = t('ortholog_not_found')
  } finally {
    geneLoading.value = false
  }
}

onMounted(async () => {
  const meta = await getOrthologMeta()
  metaList.value = meta
  await loadOgs(true)
})
</script>

<template>
  <div class="container ortholog-page">
    <h2 class="ortholog-page__title">{{ t('orthogroup') }}</h2>

    <el-tabs v-model="activeTab" class="ortholog-tabs">
      <!-- Tab 1：浏览 Orthogroup（合并后的主入口） -->
      <el-tab-pane :label="t('homology_browse')" name="browse">
        <el-row :gutter="16" class="ortholog-layout">
          <!-- 左侧：基因组复选框 -->
          <el-col :span="6" class="genome-col">
            <el-card class="genome-panel" shadow="never">
              <template #header>
                <div class="genome-panel__head">
                  <span>{{ t('ortholog_species') }}</span>
                  <el-button link type="primary" size="small" @click="toggleSelectAll">
                    {{ isAllSelected ? t('clear_all') : t('select_all') }}
                  </el-button>
                </div>
              </template>
              <el-checkbox-group v-model="selectedSpecies" class="genome-panel__list">
                <el-checkbox
                  v-for="opt in speciesOptions"
                  :key="opt.name"
                  :value="opt.name"
                  class="genome-panel__item"
                >
                  {{ opt.label }}
                </el-checkbox>
              </el-checkbox-group>
              <div class="genome-panel__count">
                {{ t('selected') }} {{ selectedSpecies.length }} / {{ allSpeciesNames.length }}
              </div>
            </el-card>
          </el-col>

          <!-- 右侧：筛选 + 列表 -->
          <el-col :span="18">
            <el-card class="ortholog-card" shadow="never">
              <div class="browse-filters">
                <el-input
                  v-model="ogIdFilter"
                  class="browse-filters__id"
                  :placeholder="t('og_id_filter_placeholder')"
                  clearable
                  size="default"
                />
                <el-input
                  v-model="annotationFilter"
                  class="browse-filters__ann"
                  :placeholder="t('annotation_filter_placeholder')"
                  clearable
                  size="default"
                />
                <el-checkbox v-model="singleCopyOnly" size="default">
                  {{ t('homology_single_copy_only') }}
                </el-checkbox>
                <el-radio-group v-if="selectedSpecies.length" v-model="speciesMode" size="default">
                  <el-radio value="all">{{ t('shared_ogs') }}</el-radio>
                  <el-radio value="any">Any</el-radio>
                </el-radio-group>
              </div>

              <el-alert v-if="ogError" type="warning" :title="ogError" show-icon class="mb-4" />

              <div class="ortholog-oglist__total">
                {{ t('total') }} {{ ogTotal }} {{ t('records') }}
              </div>

              <el-table
                v-loading="ogLoading"
                :data="filteredOgs"
                stripe
                border
                size="small"
                :row-class-name="() => 'is-clickable'"
                @sort-change="handleSortChange"
                @row-click="(row: any) => openDetail(row.og_code)"
              >
                <el-table-column :label="t('og_code')" prop="og_code" min-width="160">
                  <template #default="scope">
                    <a class="og-link">{{ scope.row.og_code }}</a>
                  </template>
                </el-table-column>
                <el-table-column
                  :label="t('species_count')"
                  prop="species_count"
                  width="140"
                  align="center"
                  sortable="custom"
                />
                <el-table-column
                  :label="t('gene_count')"
                  prop="gene_count"
                  width="130"
                  align="center"
                  sortable="custom"
                />
                <el-table-column :label="t('homology_single_copy')" width="120" align="center">
                  <template #default="scope">
                    <el-tag v-if="scope.row.is_single_copy" size="small" type="success">
                      {{ t('yes') }}
                    </el-tag>
                    <span v-else>{{ t('no') }}</span>
                  </template>
                </el-table-column>
                <el-table-column :label="t('homology_annotation')" min-width="180">
                  <template #default="scope">{{ scope.row.annotation || '-' }}</template>
                </el-table-column>
              </el-table>

              <div class="ortholog-oglist__more">
                <el-button v-if="ogHasMore" :loading="ogLoading" @click="loadMore">
                  {{ t('load_more') }}
                </el-button>
                <span v-else class="ortholog-oglist__end">{{ t('no_more') }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- Tab 2：按基因查直系同源（保留原功能） -->
      <el-tab-pane :label="t('ortholog_search')" name="gene">
        <el-card class="ortholog-card" shadow="never">
          <el-form inline @submit.prevent="searchByGene">
            <el-form-item class="ortholog-card__input">
              <el-input
                v-model="geneInput"
                :placeholder="t('ortholog_gene_placeholder')"
                clearable
                @keyup.enter="searchByGene"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="geneLoading" @click="searchByGene">
                <el-icon><Search /></el-icon>
                {{ t('search') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert v-if="geneError" type="warning" :title="geneError" show-icon class="mb-4" />
          <el-alert
            v-else-if="orthoResult && orthoResult.found"
            type="success"
            :closable="false"
            class="mb-4"
            :title="`${t('ortholog_search')}: ${orthoResult.query_gene}`"
          />

          <div v-if="orthoResult && orthoResult.found" class="ortholog-results">
            <el-card
              v-for="og in orthoResult.orthogroups"
              :key="og.og_code"
              class="ortholog-og"
              shadow="hover"
            >
              <template #header>
                <div class="ortholog-og__head">
                  <span class="ortholog-og__code">{{ og.og_code }}</span>
                  <el-tag size="small" type="primary" effect="plain">
                    {{ relationLabel(og.relation_type) }}
                  </el-tag>
                  <el-tag v-if="og.is_single_copy" size="small" type="success" effect="light">
                    {{ t('homology_single_copy') }}
                  </el-tag>
                  <span class="ortholog-og__meta">
                    {{ t('species_count') }}: {{ og.species_count }} ·
                    {{ t('gene_count') }}: {{ og.gene_count }}
                  </span>
                </div>
              </template>

              <el-table :data="og.species_members" stripe border size="small">
                <el-table-column :label="t('ortholog_species')" min-width="220">
                  <template #default="scope">{{ speciesName(scope.row) }}</template>
                </el-table-column>
                <el-table-column :label="t('ortholog_genes')" min-width="360">
                  <template #default="scope">
                    <span v-for="(g, idx) in scope.row.genes" :key="g.ortho_gene" class="ortholog-gene">
                      <a
                        v-if="g.genemaster_geneid"
                        class="ortholog-gene__link"
                        @click="openGene(g.genemaster_geneid)"
                      >{{ g.genemaster_geneid }}</a>
                      <span v-else class="ortholog-gene__plain">{{ g.ortho_gene }}</span>
                      <span
                        v-if="idx !== scope.row.genes.length - 1"
                        class="ortholog-gene__sep"
                      >, </span>
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- OG 成员明细抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      :title="(detailData?.og_code || t('og_code'))"
      size="62%"
    >
      <div v-loading="detailLoading">
        <template v-if="detailData">
          <el-descriptions :column="2" border class="mb-4">
            <el-descriptions-item :label="t('og_code')">{{ detailData.og_code }}</el-descriptions-item>
            <el-descriptions-item :label="t('species_count')">{{ detailData.species_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('gene_count')">{{ detailData.gene_count }}</el-descriptions-item>
            <el-descriptions-item :label="t('homology_single_copy')">
              {{ detailData.is_single_copy ? t('yes') : t('no') }}
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
          </div>

          <h4>{{ t('ortholog_genes') }}</h4>
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
    </el-drawer>
  </div>
</template>

<style scoped>
.ortholog-page {
  max-width: 1280px;
  margin: 0 auto;
  padding-bottom: 2rem;
}

.ortholog-page__title {
  margin-bottom: 1.25rem;
}

.ortholog-tabs {
  --el-color-primary: #3a6ea5;
}

.ortholog-layout {
  align-items: flex-start;
}

.genome-panel {
  border: 1px solid #e9ecef;
  border-radius: 12px;
  position: sticky;
  top: 16px;
}

.genome-panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.genome-panel__list {
  display: flex;
  flex-direction: column;
  max-height: 60vh;
  overflow-y: auto;
  gap: 4px;
}

.genome-panel__item {
  width: 100%;
  margin-right: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.genome-panel__count {
  margin-top: 0.75rem;
  color: #6c757d;
  font-size: 0.85rem;
}

.ortholog-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
}

.browse-filters {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.browse-filters__id {
  width: 240px;
}

.browse-filters__ann {
  width: 260px;
}

.ortholog-oglist__total {
  margin-bottom: 0.75rem;
  color: #6c757d;
  font-weight: 500;
}

.ortholog-oglist__more {
  display: flex;
  justify-content: center;
  margin-top: 1rem;
}

.ortholog-oglist__end {
  color: #adb5bd;
  font-size: 0.85rem;
}

.og-link {
  color: #3a6ea5;
  cursor: pointer;
  text-decoration: none;
}

.og-link:hover {
  text-decoration: underline;
}

.ortholog-results {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.ortholog-og {
  border: 1px solid #e9ecef;
  border-radius: 12px;
}

.ortholog-og__head {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.ortholog-og__code {
  font-weight: 600;
  font-size: 1.05rem;
  color: #3a6ea5;
}

.ortholog-og__meta {
  margin-left: auto;
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

.ortholog-card__input {
  width: 360px;
}

.mb-4 {
  margin-bottom: 1.5rem;
}
</style>
