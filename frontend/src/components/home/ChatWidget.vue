<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { ChatDotRound, Close, Promotion, Plus, Loading } from '@element-plus/icons-vue'
import { apiPost, type ApiEnvelope } from '@/utils/api'

const { t } = useI18n()

/**
 * AI 对话组件，对接后端 POST /CottonOGD_api/ai/chat/
 * 契约（服务端 ai_chat.py）：
 * - 请求 { message, clear_history? }，认证由 http.js 统一携带（Bearer / cookie）
 * - 响应 { success, answer, tool_calls: [{name, arguments, elapsed_ms}], history_turns }
 * - 对话历史保存在服务端（Redis），前端不回传历史
 */
interface ToolCall {
  name: string
  arguments?: string
  elapsed_ms?: number
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  tools?: ToolCall[]
}

const CHAT_API = '/CottonOGD_api/ai/chat/'
const AI_TIMEOUT_MS = 120000 // LLM + 工具调用可能较慢，覆盖全局 30s 超时

// Markdown 渲染：AI 回答可能包含基因 ID 列表、相对链接、表格等
marked.setOptions({ breaks: true, gfm: true })

const visible = ref(false)
const input = ref('')
const sending = ref(false)
const messages = ref<ChatMessage[]>([])
const listRef = ref<HTMLElement>()
// 点击"新话题"后置 true，下一次请求携带 clear_history 让服务端丢弃历史
const pendingClear = ref(false)

/** 将回答渲染为净化后的 HTML（DOMPurify 移除脚本/事件属性，防 XSS） */
function renderMarkdown(text: string): string {
  return DOMPurify.sanitize(marked.parse(text, { async: false }) as string)
}

function openPanel() {
  visible.value = !visible.value
  if (visible.value && messages.value.length === 0) {
    messages.value.push({ role: 'assistant', content: t('chat_welcome') })
  }
}

function startNewTopic() {
  messages.value = [{ role: 'assistant', content: t('chat_welcome') }]
  input.value = ''
  pendingClear.value = true
}

async function sendMessage() {
  const text = input.value.trim()
  if (!text || sending.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  sending.value = true
  await scrollToListEnd()

  try {
    const res = await apiPost<ApiEnvelope>(CHAT_API, { message: text, clear_history: pendingClear.value }, { timeout: AI_TIMEOUT_MS })
    pendingClear.value = false
    if (res && res.success && res.answer) {
      messages.value.push({ role: 'assistant', content: res.answer, tools: res.tool_calls })
    } else {
      messages.value.push({ role: 'assistant', content: res?.error || t('chat_error') })
    }
  } catch (e: any) {
    // http.js 对 401 已自动重登重试，这里只展示后端返回的 error 或通用提示
    const backendError = e?.response?.data?.error
    messages.value.push({ role: 'assistant', content: backendError || t('chat_error') })
  } finally {
    sending.value = false
    await scrollToListEnd()
  }
}

async function scrollToListEnd() {
  await nextTick()
  const el = listRef.value?.querySelector('.el-scrollbar__wrap')
  if (el) el.scrollTop = el.scrollHeight
}

watch(input, () => scrollToListEnd())
</script>

<template>
  <!-- 悬浮对话按钮（避开右下角回到顶部按钮） -->
  <div class="chat-fab" :title="t('chat_title')" @click="openPanel">
    <el-icon :size="24"><ChatDotRound /></el-icon>
  </div>

  <!-- 对话面板 -->
  <transition name="chat-pop">
    <div v-if="visible" class="chat-panel" role="dialog" :aria-label="t('chat_title')">
      <div class="chat-panel-header">
        <div class="chat-panel-info">
          <el-icon :size="18" class="chat-header-icon"><ChatDotRound /></el-icon>
          <div>
            <div class="chat-panel-title">{{ t('chat_title') }}</div>
            <div class="chat-panel-subtitle">{{ t('chat_subtitle') }}</div>
          </div>
        </div>
        <div class="chat-panel-actions">
          <el-button
            :title="t('chat_new')"
            circle
            size="small"
            :icon="Plus"
            @click="startNewTopic"
          />
          <el-button
            :title="t('close')"
            circle
            size="small"
            :icon="Close"
            @click="visible = false"
          />
        </div>
      </div>

      <div ref="listRef" class="chat-panel-body">
        <el-scrollbar>
          <div class="chat-messages">
            <div
              v-for="(msg, index) in messages"
              :key="index"
              class="chat-message"
              :class="msg.role"
            >
              <div class="chat-bubble">
                <!-- 用户消息纯文本插值防 XSS；AI 回答经 marked + DOMPurify 渲染 Markdown -->
                <div v-if="msg.role === 'user'" class="chat-text">{{ msg.content }}</div>
                <div v-else class="chat-text chat-md" v-html="renderMarkdown(msg.content)"></div>
                <!-- 工具调用标签：让用户知道 AI 查询了数据库 -->
                <div v-if="msg.tools && msg.tools.length" class="chat-tools">
                  <span class="chat-tools-label">{{ t('chat_tools_used') }}:</span>
                  <el-tag
                    v-for="(tool, ti) in msg.tools"
                    :key="ti"
                    size="small"
                    type="info"
                    effect="plain"
                  >
                    {{ tool.name }}
                    <template v-if="tool.elapsed_ms != null">({{ tool.elapsed_ms }}ms)</template>
                  </el-tag>
                </div>
              </div>
            </div>
            <div v-if="sending" class="chat-message assistant">
              <div class="chat-bubble chat-typing">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>{{ t('chat_thinking') }}</span>
              </div>
            </div>
          </div>
        </el-scrollbar>
      </div>

      <div class="chat-panel-footer">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          resize="none"
          :placeholder="t('chat_placeholder')"
          :disabled="sending"
          @keydown.enter.exact.prevent="sendMessage"
        />
        <el-button
          type="primary"
          class="chat-send-btn"
          :icon="Promotion"
          :loading="sending"
          :disabled="!input.trim()"
          @click="sendMessage"
        >
          {{ t('chat_send') }}
        </el-button>
      </div>
    </div>
  </transition>
</template>

<style scoped>
/* 悬浮按钮 */
.chat-fab {
  position: fixed;
  right: 40px;
  bottom: 120px; /* 避开右下角 el-backtop（bottom: 40px） */
  z-index: 2000;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: linear-gradient(135deg, #3a6ea5 0%, #7297bd 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(58, 110, 165, 0.4);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.chat-fab:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 10px 26px rgba(58, 110, 165, 0.5);
}

/* 对话面板 */
.chat-panel {
  position: fixed;
  right: 40px;
  bottom: 192px;
  z-index: 2001;
  width: 400px;
  height: 560px;
  max-width: calc(100vw - 32px);
  background: #ffffff;
  border-radius: 14px;
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.22);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.chat-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  background: linear-gradient(135deg, #3a6ea5 0%, #7297bd 100%);
  color: #ffffff;
}

.chat-panel-info {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-header-icon {
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  padding: 8px;
}

.chat-panel-title {
  font-size: 15px;
  font-weight: 600;
}

.chat-panel-subtitle {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.85);
}

.chat-panel-actions {
  display: flex;
  gap: 4px;
}

.chat-panel-body {
  flex: 1;
  min-height: 0;
  background: #f5f7fa;
}

.chat-messages {
  padding: 14px 12px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.chat-message {
  display: flex;
}

.chat-message.user {
  justify-content: flex-end;
}

.chat-message.assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: 82%;
  padding: 10px 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.55;
}

.chat-message.user .chat-bubble {
  background: #3a6ea5;
  color: #ffffff;
  border-bottom-right-radius: 4px;
}

.chat-message.assistant .chat-bubble {
  background: #ffffff;
  color: #2c3e50;
  border: 1px solid #e4e9f0;
  border-bottom-left-radius: 4px;
}

.chat-text {
  white-space: pre-wrap;
  word-break: break-word;
}

/* Markdown 渲染的 AI 回答：v-html 内容需用 :deep() 命中 */
.chat-md :deep(p) {
  margin: 0 0 8px;
}

.chat-md :deep(p:last-child) {
  margin-bottom: 0;
}

.chat-md :deep(ul),
.chat-md :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
}

.chat-md :deep(code) {
  background: rgba(58, 110, 165, 0.1);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
  word-break: break-all;
}

.chat-md :deep(pre) {
  background: #f0f3f7;
  border-radius: 8px;
  padding: 8px 10px;
  overflow-x: auto;
  margin: 6px 0;
}

.chat-md :deep(pre code) {
  background: none;
  padding: 0;
}

.chat-md :deep(table) {
  border-collapse: collapse;
  margin: 6px 0;
  font-size: 12px;
}

.chat-md :deep(th),
.chat-md :deep(td) {
  border: 1px solid #e4e9f0;
  padding: 4px 8px;
}

.chat-md :deep(a) {
  color: #3a6ea5;
}

.chat-md :deep(h1),
.chat-md :deep(h2),
.chat-md :deep(h3),
.chat-md :deep(h4) {
  font-size: 14px;
  margin: 8px 0 4px;
}

/* 工具调用标签 */
.chat-tools {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #e4e9f0;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.chat-tools-label {
  font-size: 11px;
  color: #909399;
}

/* 输入区 */
.chat-panel-footer {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid #eef2f7;
  background: #ffffff;
}

.chat-panel-footer :deep(.el-textarea__inner) {
  border-radius: 8px;
}

.chat-send-btn {
  flex-shrink: 0;
  background-color: #3a6ea5;
  border-color: #3a6ea5;
  height: 52px;
}

.chat-send-btn:hover {
  background-color: #2c5282;
  border-color: #2c5282;
}

/* "思考中"气泡 */
.chat-typing {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #909399;
}

/* 面板弹出动画 */
.chat-pop-enter-active,
.chat-pop-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}

.chat-pop-enter-from,
.chat-pop-leave-to {
  opacity: 0;
  transform: translateY(12px) scale(0.97);
}

@media (max-width: 768px) {
  .chat-fab {
    right: 16px;
    bottom: 96px;
  }
  .chat-panel {
    right: 16px;
    left: 16px;
    width: auto;
    bottom: 168px;
    height: 60vh;
  }
}
</style>
