<script setup lang="ts">
/**
 * 全局搜索框（阶段 2）
 *
 * 对标 SoyOmics 首页顶部搜索框：支持基因 ID / 区间 / 关键词的统一检索，
 * 下拉展示即时结果，点击结果跳转基因详情页，回车跳转搜索页查看全部。
 *
 * 数据来源：统一检索接口 POST /CottonOGD_api/search/（经后端代理 Meilisearch），
 * 见 src/api/index.ts 的 searchGenes / getSearchIndexes。
 *
 * 说明：本阶段只做 UI 与路由跳转，不改变任何既有页面/数据流。
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Search, Loading } from '@element-plus/icons-vue'
import { useNavigationStore } from '@/stores/modules/navigation'
import {
  searchGenes,
  getSearchIndexes,
  type SearchIndexInfo,
} from '@/api/index'
import httpInstance from '@/utils/http.js'

const { t } = useI18n()
const router = useRouter()
const navigationStore = useNavigationStore()

/** 搜索关键词 */
const keyword = ref('')
/** 是否正在检索 */
const searching = ref(false)
/** 检索耗时（ms） */
const costMs = ref(0)
/** 命中总数 */
const totalHits = ref(0)
/** 当前页命中列表 */
const hits = ref<Record<string, unknown>[]>([])
/** 错误信息 */
const errorText = ref('')
/** 检索库下拉：来自后端索引清单 */
const indexes = ref<SearchIndexInfo[]>([])
const activeIndex = ref('genemaster')
/** 是否显示结果下拉 */
const visible = ref(false)
/** 根元素，用于点击外部关闭 */
const rootRef = ref<HTMLElement | null>(null)

const indexOptions = computed(() =>
  indexes.value.filter((i) => i.available).map((i) => ({ label: i.label, value: i.uid })),
)

/** 请求序号：仅采纳最后一次请求，防竞态覆盖 */
let seq = 0
let timer: ReturnType<typeof setTimeout> | null = null

/** 执行检索 */
async function run(): Promise<void> {
  const q = keyword.value.trim()
  if (!q) {
    hits.value = []
    totalHits.value = 0
    costMs.value = 0
    errorText.value = ''
    searching.value = false
    return
  }
  const cur = ++seq
  searching.value = true
  errorText.value = ''
  try {
    const res = await searchGenes({
      q,
      index: activeIndex.value,
      offset: 0,
      limit: 8,
      withFacets: false,
    })
    if (cur !== seq) return
    if (res.code !== 0) {
      errorText.value = res.message
      hits.value = []
      totalHits.value = 0
      return
    }
    hits.value = res.data.hits
    totalHits.value = res.data.estimatedTotalHits
    costMs.value = res.data.processingTimeMs
  } catch (e) {
    if (cur === seq) {
      errorText.value = t('global_search_error')
      hits.value = []
      totalHits.value = 0
    }
  } finally {
    if (cur === seq) {
      searching.value = false
      visible.value = true
    }
  }
}

/** 输入防抖 300ms */
function onInput(): void {
  if (timer) clearTimeout(timer)
  timer = setTimeout(run, 300)
}

/** 回车：跳转搜索页查看全部结果 */
function onSubmit(): void {
  if (timer) clearTimeout(timer)
  const q = keyword.value.trim()
  if (!q) {
    errorText.value = t('global_search_enter_keyword')
    return
  }
  visible.value = false
  router.push({ name: 'idSearch', query: { query: q, index: activeIndex.value } })
}

/**
 * 点击命中项：复用项目既有的 geneid_summary 流程
 * （与 HomeView / RegionSearchView 写法一致），拉取摘要后跳 idSearchSummary。
 */
async function onPick(hit: Record<string, unknown>): Promise<void> {
  const geneid = hit.geneid as string | undefined
  if (!geneid) return
  visible.value = false
  const requestId = `gs_${Date.now()}`
  try {
    const response = (await httpInstance.post('/CottonOGD_api/geneid_summary/', {
      gene_id: geneid,
      genome_id: hit.genome_id,
      request_id: requestId,
    })) as any
    if (response && response.geneid_result) {
      const results = {
        geneid_result:
          typeof response.geneid_result === 'string'
            ? JSON.parse(response.geneid_result)
            : response.geneid_result,
        gene_info_result:
          typeof response.gene_info_result === 'string'
            ? JSON.parse(response.gene_info_result)
            : response.gene_info_result,
        search_map:
          typeof response.search_map === 'string'
            ? JSON.parse(response.search_map)
            : response.search_map,
        gene_go_result: response.gene_go_result || [],
        gene_kegg_result: response.gene_kegg_result || [],
      }
      const dbIds = results.search_map
        ? Object.values(results.search_map)
            .map((item: any) => item?.db_id)
            .filter(Boolean)
        : []
      navigationStore.setNavigationData('geneSearch', {
        results,
        dbIds,
        requestId,
      })
      router.push({ name: 'idSearchSummary' })
    } else {
      errorText.value = t('global_search_error')
    }
  } catch {
    errorText.value = t('global_search_error')
  }
}

/** 点击组件外部关闭下拉 */
function onClickOutside(event: MouseEvent): void {
  const el = rootRef.value
  if (el && event.target instanceof Node && !el.contains(event.target)) {
    visible.value = false
  }
}

onMounted(async () => {
  document.addEventListener('click', onClickOutside)
  // 拉取可用检索库；失败时保持空（下拉仅剩默认项）
  const res = await getSearchIndexes()
  if (res.code === 0 && res.data.length) {
    indexes.value = res.data
    const first = res.data.find((i) => i.available)
    if (first) activeIndex.value = first.uid
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onClickOutside)
  if (timer) clearTimeout(timer)
})

/** 取字段用于展示：优先高亮片段 */
function hitText(hit: Record<string, unknown>, field: string): string {
  const formatted = hit._formatted as Record<string, string> | undefined
  const value = formatted?.[field] ?? (hit[field] as string | undefined)
  return value ?? ''
}
</script>

<template>
  <div ref="rootRef" class="global-search">
    <el-input
      v-model="keyword"
      class="global-search__input"
      :placeholder="t('global_search_placeholder')"
      clearable
      size="large"
      :suffix-icon="searching ? Loading : Search"
      @input="onInput"
      @keyup.enter="onSubmit"
      @clear="hits = []"
      @focus="keyword.trim() && (visible = true)"
    >
      <template v-if="indexOptions.length" #prepend>
        <el-select v-model="activeIndex" class="global-search__index" size="large">
          <el-option
            v-for="opt in indexOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </template>
    </el-input>

    <!-- 即时结果下拉 -->
    <transition name="el-zoom-in-top">
      <div v-if="visible" class="global-search__panel">
        <div v-if="searching" class="global-search__state">
          <el-icon class="is-loading"><Loading /></el-icon>
          <span>{{ t('search') }}...</span>
        </div>

        <el-alert
          v-else-if="errorText"
          :title="errorText"
          type="error"
          show-icon
          :closable="false"
        />

        <div v-else-if="hits.length === 0" class="global-search__state">
          <span>{{ t('no_search_results_data_please_search_again') }}</span>
        </div>

        <template v-else>
          <ul class="global-search__list">
            <li
              v-for="(hit, idx) in hits"
              :key="(hit.id as string) || idx"
              class="global-search__item"
              :class="{ 'is-clickable': !!hit.geneid }"
              @click="onPick(hit)"
            >
              <div class="global-search__main">
                <span
                  v-if="hit.geneid"
                  class="global-search__geneid"
                  v-html="hitText(hit, 'geneid')"
                ></span>
                <span v-else class="global-search__geneid">{{ hit.id }}</span>
                <span
                  v-if="hit.alias"
                  class="global-search__alias"
                  v-html="hitText(hit, 'alias')"
                ></span>
              </div>
              <el-tag v-if="hit.genome_id" size="small" type="success" effect="light">
                {{ hit.genome_id }}
              </el-tag>
            </li>
          </ul>

          <div class="global-search__footer">
            <span>~{{ totalHits.toLocaleString() }} hits · {{ costMs }} ms</span>
            <el-button link type="primary" size="small" @click="onSubmit">
              {{ t('global_search_see_all') }}
            </el-button>
          </div>
        </template>
      </div>
    </transition>
  </div>
</template>

<style scoped>
.global-search {
  position: relative;
  width: 100%;
}

.global-search__index {
  width: 150px;
}

.global-search__panel {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  z-index: 2000;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0.12);
  overflow: hidden;
}

.global-search__state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 20px 12px;
  color: #6c757d;
  font-size: 14px;
}

.global-search__list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 360px;
  overflow-y: auto;
}

.global-search__item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  border-bottom: 1px solid #f1f3f5;
}

.global-search__item:last-child {
  border-bottom: none;
}

.global-search__item.is-clickable {
  cursor: pointer;
}

.global-search__item.is-clickable:hover {
  background-color: #f0f6ff;
}

.global-search__main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.global-search__geneid {
  font-weight: 600;
  color: #2c3e50;
  font-size: 14px;
}

.global-search__geneid :deep(em) {
  font-style: normal;
  color: #e6a23c;
  font-weight: 700;
}

.global-search__alias {
  font-size: 12px;
  color: #6c757d;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.global-search__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  border-top: 1px solid #eef2f7;
  font-size: 12px;
  color: #6c757d;
}
</style>
