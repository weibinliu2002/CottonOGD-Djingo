<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { apiGet } from '@/utils/api'

const { t } = useI18n()

/**
 * 首页新闻公告框：位于"物种基因组大小"散点图右侧。
 * onMounted 时尝试从后端 /CottonOGD_api/news/ 拉取；接口未上线或失败时
 * 静默回退为空占位，不影响首页其他功能。
 */
interface NewsItem {
  date: string
  type: 'update' | 'release' | 'publication' | 'event'
  title: string
  summary: string
  link?: string
}

const NEWS_API = '/CottonOGD_api/news/'
const VALID_TYPES = new Set(['update', 'release', 'publication', 'event'])
const newsItems = ref<NewsItem[]>([])
const loaded = ref(false)

/** 宽松校验后端条目：字段缺失/类型非法的条目跳过，避免脏数据打崩首页 */
function normalizeItem(raw: Record<string, unknown>): NewsItem | null {
  if (typeof raw !== 'object' || raw === null) return null
  const title = typeof raw.title === 'string' ? raw.title : ''
  if (!title) return null
  return {
    date: typeof raw.date === 'string' ? raw.date : '',
    type: VALID_TYPES.has(raw.type as string) ? (raw.type as NewsItem['type']) : 'update',
    title,
    summary: typeof raw.summary === 'string' ? raw.summary : '',
    link: typeof raw.link === 'string' ? raw.link : undefined,
  }
}

onMounted(async () => {
  try {
    const res = await apiGet<unknown[]>(NEWS_API)
    const list = Array.isArray(res) ? res : Array.isArray((res as any)?.data) ? (res as any).data : []
    newsItems.value = list.map(normalizeItem).filter((it: NewsItem | null): it is NewsItem => it !== null)
  } catch {
    // 新闻接口尚未上线：保持空占位
  } finally {
    loaded.value = true
  }
})

const typeTagMap: Record<NewsItem['type'], { label: string; kind: 'primary' | 'success' | 'warning' | 'info' }> = {
  update: { label: 'Update', kind: 'primary' },
  release: { label: 'Release', kind: 'success' },
  publication: { label: 'Publication', kind: 'warning' },
  event: { label: 'Event', kind: 'info' },
}
</script>

<template>
  <div class="news-box">
    <div class="news-header">
      <h3 class="news-title">
        <i class="fas fa-bullhorn"></i>
        {{ t('news_title') }}
      </h3>
    </div>
    <div class="news-body">
      <!-- 有内容时的列表 -->
      <el-scrollbar v-if="newsItems.length" max-height="380px">
        <ul class="news-list">
          <li v-for="(item, index) in newsItems" :key="index" class="news-item">
            <div class="news-date">{{ item.date }}</div>
            <div class="news-body-main">
              <div class="news-item-title">
                <el-tag size="small" :type="typeTagMap[item.type].kind" effect="light" class="news-tag">
                  {{ typeTagMap[item.type].label }}
                </el-tag>
                <component
                  :is="item.link ? 'router-link' : 'span'"
                  :to="item.link"
                  class="news-link"
                >
                  {{ item.title }}
                </component>
              </div>
              <p class="news-summary">{{ item.summary }}</p>
            </div>
          </li>
        </ul>
      </el-scrollbar>
      <!-- 空内容占位 -->
      <div v-else class="news-placeholder">
        <i class="fas fa-newspaper"></i>
        <p>{{ t('news_empty') }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.news-box {
  height: 100%;
  min-height: 300px;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.news-header {
  border-bottom: 1px solid #eef2f7;
  padding-bottom: 12px;
  margin-bottom: 8px;
  flex-shrink: 0;
}

.news-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #3a6ea5;
  display: flex;
  align-items: center;
  gap: 8px;
}

.news-body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

/* 空内容占位：撑满剩余高度居中显示 */
.news-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: #b0b7c3;
  min-height: 220px;
}

.news-placeholder i {
  font-size: 40px;
}

.news-placeholder p {
  margin: 0;
  font-size: 13px;
}

.news-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.news-item {
  display: flex;
  gap: 12px;
  padding: 12px 4px;
  border-bottom: 1px dashed #eef2f7;
}

.news-item:last-child {
  border-bottom: none;
}

.news-date {
  flex-shrink: 0;
  width: 74px;
  font-size: 12px;
  color: #909399;
  padding-top: 2px;
}

.news-body-main {
  min-width: 0;
  flex: 1;
}

.news-item-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.news-link {
  color: #2c3e50;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  cursor: pointer;
}

a.news-link:hover {
  color: #3a6ea5;
}

span.news-link {
  cursor: default;
}

.news-summary {
  margin: 6px 0 0;
  font-size: 12px;
  color: #6c757d;
  line-height: 1.5;
}

.news-tag {
  flex-shrink: 0;
}
</style>
