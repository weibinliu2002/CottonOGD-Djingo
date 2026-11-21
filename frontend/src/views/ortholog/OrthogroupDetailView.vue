<script setup lang="ts">
/**
 * 单个 Orthogroup 详情页（阶段 5.2，2026-11 升级）。
 *
 * 路由：/tools/orthogroup/:og_code —— 例如 /tools/orthogroup/OG0000000
 * 从 OG 浏览列表、按基因查、主页检索均可深链进入。
 *
 * 页面结构：顶部返回/OG 编号 → OrthogroupAnalysis 面板（复用于浏览页抽屉）。
 * 面板包含：概览与基因组分布、成员分页、真实直系同源、HOG、复制事件、
 *           MSA、基因树、OG 序列；各模块按需加载、独立失败互不阻塞。
 *
 * 数据口径遵循 v1 契约：服务器 backend/docs/api/endpoints.md 与前端
 * docs/COMPARATIVE_ANALYSIS_API_HANDOFF.md（2026-11-21 按 v1 重写）。
 */
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { CopyDocument } from '@element-plus/icons-vue'
import OrthogroupAnalysis from '@/components/data-display/OrthogroupAnalysis.vue'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const ogCode = computed(() => (route.params.og_code as string) || '')

/**
 * 从浏览页带过来的「只看所选基因组」筛选（route.query.species 逗号分隔）。
 * 主页 `?og=` 深链或全选进入时无该 query，则显示全部基因组成员。
 */
const selectedSpeciesFilter = computed<string[]>(() => {
  const raw = route.query.species
  if (Array.isArray(raw)) return raw.filter(Boolean) as string[]
  if (typeof raw === 'string' && raw.trim()) return raw.split(',').filter(Boolean)
  return []
})

function backToList(): void {
  router.push({ name: 'Orthogroup' })
}

/** 复制 OG 编号（沿用旧详情页功能） */
function copyOgCode(): void {
  if (!ogCode.value) return
  navigator.clipboard?.writeText(ogCode.value).catch(() => {})
}
</script>

<template>
  <div class="container og-detail">
    <div class="og-detail__nav">
      <el-button link type="primary" size="small" @click="backToList">
        ← {{ t('orthogroup') }}
      </el-button>
      <span class="og-detail__code">{{ ogCode }}</span>
      <el-button
        v-if="ogCode"
        size="small"
        :icon="CopyDocument"
        @click="copyOgCode"
      >{{ t('copy_og_code') }}</el-button>
    </div>

    <el-card class="og-card" shadow="never">
      <OrthogroupAnalysis
        v-if="ogCode"
        :og-code="ogCode"
        :species-filter="selectedSpeciesFilter"
      />
      <el-empty v-else :description="t('no_data')" />
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
}
</style>
