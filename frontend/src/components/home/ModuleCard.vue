<script setup lang="ts">
/**
 * 模块入口卡片（阶段 3.1）
 *
 * 对标 SoyOmics 首页六大模块入口：图标 + 标题 + 描述 + 内部快捷链接。
 * 支持"未开放"状态（disabled），此时卡片置灰且点击不做跳转。
 */
import { useRouter, type RouteLocationRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'

interface QuickLink {
  /** 展示文案（i18n key） */
  labelKey: string
  /** 跳转目标 */
  to: RouteLocationRaw
}

const props = defineProps<{
  /** 标题 i18n key */
  titleKey: string
  /** 描述 i18n key */
  descKey: string
  /** FontAwesome 图标类名，如 'fas fa-dna' */
  icon: string
  /** 快捷链接列表 */
  links: QuickLink[]
  /** 是否未开放 */
  disabled?: boolean
  /** 图标背景色 */
  color?: string
}>()

const { t } = useI18n()
const router = useRouter()

/** 点击卡片主体：跳转到第一个快捷链接 */
function onCardClick(): void {
  if (props.disabled) return
  const first = props.links[0]
  if (first) router.push(first.to)
}

/** 点击内部链接：阻止冒泡，避免重复触发卡片跳转 */
function onLinkClick(event: MouseEvent, link: QuickLink): void {
  event.stopPropagation()
  if (props.disabled) return
  router.push(link.to)
}
</script>

<template>
  <div class="module-card" :class="{ 'is-disabled': disabled }" @click="onCardClick">
    <div class="module-card__icon" :style="{ background: color || '#3a6ea5' }">
      <i :class="icon" />
    </div>
    <h3 class="module-card__title">{{ t(titleKey) }}</h3>
    <p class="module-card__desc">{{ t(descKey) }}</p>

    <div class="module-card__links">
      <template v-if="!disabled">
        <a
          v-for="link in links"
          :key="link.labelKey"
          class="module-card__link"
          href="javascript:void(0)"
          @click="onLinkClick($event, link)"
        >
          {{ t(link.labelKey) }}
        </a>
      </template>
      <span v-else class="module-card__soon">{{ t('module_coming_soon') }}</span>
    </div>
  </div>
</template>

<style scoped>
.module-card {
  height: 100%;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 12px;
  padding: 24px 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.3s ease;
  display: flex;
  flex-direction: column;
}

.module-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 12px 24px rgba(0, 0, 0.1);
  border-color: #3a6ea5;
}

.module-card.is-disabled {
  cursor: default;
  opacity: 0.72;
}

.module-card.is-disabled:hover {
  transform: none;
  box-shadow: none;
  border-color: #e9ecef;
}

.module-card__icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 26px;
}

.module-card__title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.module-card__desc {
  margin: 0 0 16px;
  font-size: 13px;
  line-height: 1.6;
  color: #6c757d;
  flex: 1;
}

.module-card__links {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.module-card__link {
  font-size: 12px;
  color: #3a6ea5;
  text-decoration: none;
  border: 1px solid #d7e3f0;
  border-radius: 999px;
  padding: 3px 10px;
  transition: all 0.2s ease;
}

.module-card__link:hover {
  background-color: #3a6ea5;
  border-color: #3a6ea5;
  color: #ffffff;
}

.module-card__soon {
  font-size: 12px;
  color: #909399;
}
</style>
