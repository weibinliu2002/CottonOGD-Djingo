<template>
  <div class="container-fluid">
    <div class="row">
      <!-- 左侧边栏 -->
      <div class="col-md-3">
        <div class="sidebar">
          <h3>{{ t('phylotree') }}</h3>
          <div class="mt-4">
            <h4 class="sidebar-title">
              <el-icon><VideoPlay /></el-icon> {{ t('select_genome') }}
            </h4>
            <el-cascader
              v-model="selectedGenome"
              :options="filteredGenomeOptions"
              :props="cascaderProps"
              :placeholder="t('select_genome')"
              class="w-100 mt-2"
              @change="handleGenomeChange"
              :loading="genomeLoading"
            />
            <div v-if="genomeChecking" class="genome-checking">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>{{ t('genome_checking_trees') }}</span>
            </div>
          </div>
          <div class="mt-4">
            <h4 class="sidebar-title">
              <el-icon><VideoPlay /></el-icon> {{ t('category') }}
            </h4>
            <el-radio-group
              v-model="treeCategory"
              class="mt-2"
              @change="handleCategoryChange"
            >
              <el-radio value="TF">{{ t('tf') }}</el-radio>
              <el-radio value="TR">{{ t('tr') }}</el-radio>
            </el-radio-group>
          </div>
        </div>
      </div>

      <!-- 主内容区域 -->
      <div class="col-md-9">
        <div class="main-content">
          <h2>{{ t('transcription_factor_phylotree') }}</h2>
          <PhylocanvasViewer
            v-if="selectedGenomeName"
            :key="treeKey"
            :genome="selectedGenomeName"
            :category="treeCategory"
          />
          <el-empty v-else :description="t('select_genome_first')" />
        </div>
      </div>
    </div>

    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<style scoped>
.container-fluid {
  padding: 20px;
  background-color: #f5f5f5;
  min-height: 100vh;
}

.sidebar {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  height: fit-content;
}

.sidebar h3 {
  font-size: 1.2rem;
  font-weight: bold;
  color: #3a6ea5;
}

.sidebar-title {
  font-size: 1rem;
  font-weight: bold;
  color: #333;
  margin-bottom: 0;
  display: flex;
  align-items: center;
  gap: 4px;
}

.genome-checking {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  font-size: 12px;
  color: #909399;
}

.main-content {
  background-color: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  min-height: 600px;
}

.main-content h2 {
  font-size: 1.5rem;
  font-weight: bold;
  color: #3a6ea5;
  margin-bottom: 20px;
}

.w-100 {
  width: 100%;
}
</style>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { VideoPlay, Loading } from '@element-plus/icons-vue'
import PhylocanvasViewer from '@/components/data-display/PhylocanvasViewer.vue'
import { useGenomeSelector } from '@/composables/features/useGenomeBrowser'

const { t } = useI18n()

// 默认基因组为 TM-1_HAU（composable 内置 DEFAULT_GENOME）
const {
  selectedGenome,
  genomeOptions,
  genomeLoading,
  allGenomes,
  cascaderProps,
  ensureGenomesLoaded,
  pickDefaultGenome
} = useGenomeSelector()

const selectedGenomeName = computed(() => {
  if (!selectedGenome.value.length) return ''
  return selectedGenome.value[selectedGenome.value.length - 1]
})

const treeCategory = ref<'TF' | 'TR'>('TF')
const treeKey = ref(0)

// ==================== 无树文件基因组过滤 ====================
// 后端 tf_tree 接口按 基因组/类别/家族 提供树文件，部分基因组没有树。
// 用每个基因组的前几个家族做 HEAD 探测，命中任意一个即视为可用；
// 探测结果按「类别|基因组」缓存，切换类别只补探测新类别。
const PROBE_FAMILIES: Record<'TF' | 'TR', string[]> = {
  TF: ['Alfin-like', 'AP2', 'ARF'],
  // 注意：家族名不得含 “/”。含斜杠的名称（如 AUX/IAA）在服务器上会落到 SPA 兜底路由，
  // 返回 200 + text/html，会造成“全部基因组都有树”的误判，因此只探测 URL 安全的家族名。
  TR: ['ARID', 'GNAT', 'PHD']
}
const PROBE_CONCURRENCY = 6
const probeCache = new Map<string, boolean>()

const availableGenomes = ref<Set<string> | null>(null)
const genomeChecking = ref(false)

const filteredGenomeOptions = computed(() => {
  const pool = availableGenomes.value
  if (!pool) return genomeOptions.value
  return genomeOptions.value
    .map((group) => ({
      ...group,
      children: (group.children || []).filter((item) => pool.has(item.value))
    }))
    .filter((group) => (group.children?.length ?? 0) > 0)
})


/** 级联选择器的 v-model 需要完整路径（分组值 + 基因组值），否则过滤后回显为空 */
function selectGenome(name: string) {
  if (!name) {
    selectedGenome.value = []
    return
  }
  const group = genomeOptions.value.find((g) => (g.children || []).some((c) => c.value === name))
  selectedGenome.value = group ? [group.value, name] : [name]
}

/** 判断响应是否真的是树文件：SPA 兜底会返回 200 的 HTML 页面，不能当作存在 */
function isTreeFileResponse(res: Response): boolean {
  if (!res.ok && res.status !== 206) return false
  const type = (res.headers.get('content-type') || '').toLowerCase()
  return !type.includes('text/html')
}

async function probeTreeFile(genome: string, family: string): Promise<boolean> {
  const url = `/CottonOGD_api/tf_tree/tree/genome/${encodeURIComponent(genome)}/${treeCategory.value}/${encodeURIComponent(family)}.treefile`
  try {
    const res = await fetch(url, { method: 'HEAD' })
    if (res.status === 405 || res.status === 501) {
      // 少数服务端不支持 HEAD，退回 Range GET 只取首字节
      const ranged = await fetch(url, { headers: { Range: 'bytes=0-0' } })
      return isTreeFileResponse(ranged)
    }
    return isTreeFileResponse(res)
  } catch {
    // 网络异常（含浏览器中止并发 HEAD）按不可用处理，宁可少列基因组也不能把无树基因组放进来；
    // 先重试一次以排除偶发中止
    try {
      const retry = await fetch(url, { headers: { Range: 'bytes=0-0' } })
      return isTreeFileResponse(retry)
    } catch {
      return false
    }
  }
}

async function probeGenome(genome: string): Promise<boolean> {
  const key = `${treeCategory.value}|${genome}`
  const cached = probeCache.get(key)
  if (cached !== undefined) return cached
  let available = false
  for (const family of PROBE_FAMILIES[treeCategory.value]) {
    // eslint-disable-next-line no-await-in-loop
    if (await probeTreeFile(genome, family)) {
      available = true
      break
    }
  }
  probeCache.set(key, available)
  return available
}

async function filterGenomesByTree() {
  const names = allGenomes.value
  if (!names.length) return
  genomeChecking.value = true
  const result = new Set<string>()
  const queue = [...names]

  const worker = async () => {
    while (queue.length) {
      const name = queue.shift()
      if (!name) break
      // eslint-disable-next-line no-await-in-loop
      if (await probeGenome(name)) result.add(name)
    }
  }

  try {
    await Promise.all(Array.from({ length: PROBE_CONCURRENCY }, worker))
  } finally {
    genomeChecking.value = false
  }

  // 全部探测失败（比如接口不可用）时不做过滤，保留原始列表
  if (result.size === 0) return
  availableGenomes.value = result

  if (selectedGenomeName.value && !result.has(selectedGenomeName.value)) {
    const preferred = pickDefaultGenome()
    const fallback = result.has(preferred)
      ? preferred
      : filteredGenomeOptions.value[0]?.children?.[0]?.value || ''
    selectGenome(fallback)
    treeKey.value++
  }
}

function handleGenomeChange() {
  treeKey.value++
}

async function handleCategoryChange() {
  treeKey.value++
  await filterGenomesByTree()
  // 新类别下当前基因组可能没有树，若可用集合已更新则重新校验
  if (availableGenomes.value && selectedGenomeName.value
    && !availableGenomes.value.has(selectedGenomeName.value)) {
    const fallback = filteredGenomeOptions.value[0]?.children?.[0]?.value || ''
    selectGenome(fallback)
    treeKey.value++
  }
}

onMounted(async () => {
  await ensureGenomesLoaded()
  selectGenome(pickDefaultGenome())
  await filterGenomesByTree()
})
</script>