<script setup lang="ts">
/**
 * 直系同源 / Orthogroup 查询页（阶段 5.1）
 *
 * 对标 SoyOmics 的同源模块，分两个 Tab：
 *  1. 按基因查直系同源：输入基因 id → 展示该基因所属每个 OG 的跨物种同源表格，
 *     行=物种，列=成员基因（genemaster_geneid 有值则跳基因详情页，否则展示 ortho_gene）。
 *  2. 按物种筛选 OG：多选物种 → 列出共有/任一 OG，点 OG 展开成员明细。
 *
 * 所有接口走统一 api 层的后端真实路由 /CottonOGD_api/orthofinder/，
 * 不依赖任何 mock（后端接口已就绪）。
 */
import { ref, computed, onMounted } from 'vue'
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

const activeTab = ref<'gene' | 'species'>('gene')

// ============ Tab 1：按基因查直系同源 ============
const geneInput = ref('')
const geneLoading = ref(false)
const geneError = ref('')
const orthoResult = ref<{ query_gene: string; found: boolean; orthogroups: OrthologOrthogroup[] } | null>(null)

/** relation_type → i18n 标签（single/none 回退到原始值） */
function relationLabel(type: string): string {
  const map: Record<string, string> = {
    one_to_one: t('one_to_one'),
    one_to_many: t('one_to_many'),
    many_to_one: t('many_to_one'),
    many_to_many: t('many_to_many'),
  }
  return map[type] ?? type
}

/** 物种展示名：display_name 优先，回退 species */
function speciesName(member: OrthologSpeciesMember): string {
  return member.display_name || member.species
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

/** genemaster_geneid 有值则跳基因详情页，否则无操作（展示 ortho_gene） */
function openGene(genemasterGeneid: string | null): void {
  if (!genemasterGeneid) return
  router.push({ name: 'GenomeDetail', params: { key: genemasterGeneid } })
}

// ============ Tab 2：按物种筛选 OG ============
const metaList = ref<OrthologSpeciesMeta[]>([])
const selectedSpecies = ref<string[]>([])
const speciesMode = ref<'all' | 'any'>('all')
const ogLimit = ref(50)
const ogOffset = ref(0)
const ogList = ref<OrthologOrthogroup[]>([])
const ogTotal = ref(0)
const ogLoading = ref(false)
const ogError = ref('')
const ogHasMore = computed(() => ogList.value.length < ogTotal.value)

/** 物种下拉选项：alias / Cotton_Species 优先，回退 name */
const speciesOptions = computed(() =>
  metaList.value.map((m) => ({
    name: m.name,
    label: m.alias || m.Cotton_Species || m.name,
  })),
)

/** 展开某个 OG 的成员明细 */
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref<OrthologOrthogroup | null>(null)

async function openDetail(ogCode: string): Promise<void> {
  detailVisible.value = true
  detailLoading.value = true
  detailData.value = null
  try {
    detailData.value = await getOrthogroupDetailV2(ogCode)
  } finally {
    detailLoading.value = false
  }
}

/** 按物种筛选 OG：offset=0 时重置列表 */
async function loadBySpecies(reset = true): Promise<void> {
  if (selectedSpecies.value.length === 0) {
    ogError.value = t('species_filter')
    return
  }
  ogLoading.value = true
  ogError.value = ''
  if (reset) {
    ogOffset.value = 0
    ogList.value = []
  }
  try {
    const res = await getOrthogroupsBySpecies({
      species: selectedSpecies.value,
      mode: speciesMode.value,
      limit: ogLimit.value,
      offset: ogOffset.value,
    })
    ogTotal.value = res.total ?? 0
    if (reset) {
      ogList.value = res.orthogroups ?? []
    } else {
      ogList.value = [...ogList.value, ...(res.orthogroups ?? [])]
    }
    if (!res.found && ogList.value.length === 0) {
      ogError.value = t('ortholog_not_found')
    }
  } catch {
    ogError.value = t('ortholog_not_found')
  } finally {
    ogLoading.value = false
  }
}

/** 加载下一页（自管 offset） */
function loadMore(): void {
  if (!ogHasMore.value || ogLoading.value) return
  ogOffset.value += ogLimit.value
  loadBySpecies(false)
}

onMounted(async () => {
  const meta = await getOrthologMeta()
  metaList.value = meta
})
</script>

<template>
  <div class="container ortholog-page">
    <h2 class="ortholog-page__title">{{ t('orthogroup') }}</h2>

    <el-tabs v-model="activeTab" class="ortholog-tabs">
      <!-- Tab 1：按基因查直系同源 -->
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
                  <el-tag size="small" type="primary" effect="plain">{{ relationLabel(og.relation_type) }}</el-tag>
                  <el-tag v-if="og.is_single_copy" size="small" type="success" effect="light">
                    {{ t('homology_single_copy') }}
                  </el-tag>
                  <span class="ortholog-og__meta">
                    {{ t('species_count') }}: {{ og.species_count }} · {{ t('gene_count') }}: {{ og.gene_count }}
                  </span>
                </div>
              </template>

              <el-table :data="og.species_members" stripe border size="small">
                <el-table-column :label="t('ortholog_species')" min-width="220">
                  <template #default="scope">{{ speciesName(scope.row) }}</template>
                </el-table-column>
                <el-table-column :label="t('ortholog_genes')" min-width="360">
                  <template #default="scope">
                    <span
                      v-for="(g, idx) in scope.row.genes"
                      :key="g.ortho_gene"
                      class="ortholog-gene"
                    >
                      <a
                        v-if="g.genemaster_geneid"
                        class="ortholog-gene__link"
                        @click="openGene(g.genemaster_geneid)"
                      >{{ g.genemaster_geneid }}</a>
                      <span v-else class="ortholog-gene__plain">{{ g.ortho_gene }}</span>
                      <span class="ortholog-gene__sep" v-if="idx !== scope.row.genes.length - 1">, </span>
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </el-card>
          </div>
        </el-card>
      </el-tab-pane>

      <!-- Tab 2：按物种筛选 OG -->
      <el-tab-pane :label="t('species_filter')" name="species">
        <el-card class="ortholog-card" shadow="never">
          <el-form inline>
            <el-form-item :label="t('ortholog_species')">
              <el-select
                v-model="selectedSpecies"
                multiple
                filterable
                collapse-tags
                :placeholder="t('species_filter')"
                class="ortholog-card__select"
              >
                <el-option
                  v-for="opt in speciesOptions"
                  :key="opt.name"
                  :label="opt.label"
                  :value="opt.name"
                />
              </el-select>
            </el-form-item>
            <el-form-item :label="t('shared_ogs')">
              <el-radio-group v-model="speciesMode">
                <el-radio value="all">{{ t('shared_ogs') }}</el-radio>
                <el-radio value="any">Any</el-radio>
              </el-radio-group>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="ogLoading" @click="loadBySpecies(true)">
                <el-icon><Search /></el-icon>
                {{ t('search') }}
              </el-button>
            </el-form-item>
          </el-form>

          <el-alert v-if="ogError" type="warning" :title="ogError" show-icon class="mb-4" />

          <div v-if="ogList.length" class="ortholog-oglist">
            <div class="ortholog-oglist__total">
              {{ t('total') }} {{ ogTotal }} {{ t('orthogroup') }}
            </div>
            <el-table :data="ogList" stripe border size="small" @row-click="(row: any) => openDetail(row.og_code)">
              <el-table-column :label="t('og_code')" prop="og_code" min-width="160">
                <template #default="scope">
                  <a class="ortholog-gene__link">{{ scope.row.og_code }}</a>
                </template>
              </el-table-column>
              <el-table-column :label="t('species_count')" prop="species_count" width="140" align="center" />
              <el-table-column :label="t('gene_count')" prop="gene_count" width="140" align="center" />
              <el-table-column :label="t('homology_single_copy')" width="120" align="center">
                <template #default="scope">
                  <el-tag v-if="scope.row.is_single_copy" size="small" type="success">{{ t('yes') }}</el-tag>
                  <span v-else>{{ t('no') }}</span>
                </template>
              </el-table-column>
            </el-table>

            <div class="ortholog-oglist__more">
              <el-button v-if="ogHasMore" :loading="ogLoading" @click="loadMore">
                {{ t('load_more') || 'Load more' }}
              </el-button>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- OG 成员明细抽屉 -->
    <el-drawer v-model="detailVisible" :title="detailData?.og_code || t('og_code')" size="60%">
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

          <h4>{{ t('ortholog_genes') }}</h4>
          <el-table :data="detailData.species_members" stripe border size="small">
            <el-table-column :label="t('ortholog_species')" min-width="220">
              <template #default="scope">{{ speciesName(scope.row) }}</template>
            </el-table-column>
            <el-table-column :label="t('ortholog_genes')" min-width="420">
              <template #default="scope">
                <span v-for="(g, idx) in scope.row.genes" :key="g.ortho_gene" class="ortholog-gene">
                  <a
                    v-if="g.genemaster_geneid"
                    class="ortholog-gene__link"
                    @click="openGene(g.genemaster_geneid)"
                  >{{ g.genemaster_geneid }}</a>
                  <span v-else class="ortholog-gene__plain">{{ g.ortho_gene }}</span>
                  <span class="ortholog-gene__sep" v-if="idx !== scope.row.genes.length - 1">, </span>
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
  max-width: 1200px;
  margin: 0 auto;
  padding-bottom: 2rem;
}

.ortholog-page__title {
  margin-bottom: 1.25rem;
}

.ortholog-tabs {
  --el-color-primary: #3a6ea5;
}

.ortholog-card {
  border: 1px solid #e9ecef;
  border-radius: 12px;
}

.ortholog-card__input {
  width: 360px;
}

.ortholog-card__select {
  width: 420px;
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

.mb-4 {
  margin-bottom: 1.5rem;
}
</style>
