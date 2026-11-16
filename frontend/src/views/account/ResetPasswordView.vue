<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute } from 'vue-router'
import { ArrowRight, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/modules/auth'
import { getAuthErrorMessage } from '@/utils/authError'

const { t } = useI18n()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref()
const loading = ref(false)
const submitted = ref(false)
const form = ref({ password: '', confirmPassword: '' })
const uidb36 = computed(() => {
  const value = route.params.uidb36 ?? route.query.uidb36
  return typeof value === 'string' ? value : ''
})
const resetKey = computed(() => {
  const value = route.params.key ?? route.query.key
  return typeof value === 'string' ? value : ''
})
const hasResetLink = computed(() => Boolean(uidb36.value && resetKey.value))

const validatePassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value.length < 8 || !/[A-Za-z]/.test(value) || !/\d/.test(value)) {
    callback(new Error(t('auth_password_strength')))
    return
  }
  callback()
}
const validateConfirmPassword = (_rule: unknown, value: string, callback: (error?: Error) => void) => {
  if (value !== form.value.password) {
    callback(new Error(t('auth_password_mismatch')))
    return
  }
  callback()
}
const rules = {
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

async function submit() {
  if (loading.value || submitted.value || !hasResetLink.value) return

  loading.value = true
  try {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return

    await authStore.resetPassword(uidb36.value, resetKey.value, form.value.password)
    submitted.value = true
  } catch (error) {
    ElMessage.error(getAuthErrorMessage(error, t('auth_request_failed')))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="account-page">
    <div class="account-card">
      <div class="account-heading">
        <div class="account-mark"><Lock /></div>
        <p class="account-eyebrow">iCotton</p>
        <h1>{{ submitted ? t('auth_reset_success_title') : t('auth_reset_title') }}</h1>
        <p class="account-description">
          {{ submitted ? t('auth_reset_success_description') : t('auth_reset_description') }}
        </p>
      </div>

      <template v-if="submitted">
        <el-result icon="success" :title="t('auth_reset_success_title')" />
        <el-button type="primary" size="large" class="account-submit" @click="$router.push('/login')">
          {{ t('auth_back_to_login') }}
        </el-button>
      </template>

      <template v-else-if="!hasResetLink">
        <el-alert
          :title="t('auth_reset_link_missing')"
          type="warning"
          :closable="false"
          show-icon
        />
        <el-button type="primary" size="large" class="account-submit" @click="$router.push('/forgot-password')">
          {{ t('auth_forgot_title') }}
        </el-button>
      </template>

      <el-form v-else ref="formRef" :model="form" :rules="rules" @submit.prevent="submit">
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            :placeholder="t('auth_new_password')"
            size="large"
            type="password"
            autocomplete="new-password"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-form-item prop="confirmPassword">
          <el-input
            v-model="form.confirmPassword"
            :placeholder="t('auth_confirm_password')"
            size="large"
            type="password"
            autocomplete="new-password"
            show-password
            :prefix-icon="Lock"
          />
        </el-form-item>
        <el-button
          type="primary"
          native-type="submit"
          size="large"
          class="account-submit"
          :loading="loading"
        >
          {{ t('auth_reset_password') }}
          <el-icon class="submit-icon"><ArrowRight /></el-icon>
        </el-button>
      </el-form>
    </div>
  </section>
</template>

<style scoped>
.account-page {
  display: flex;
  justify-content: center;
  padding: 64px 16px 80px;
}

.account-card {
  width: min(100%, 440px);
  padding: 36px;
  border: 1px solid #e9ecef;
  border-radius: 16px;
  background: #fff;
  box-shadow: 0 16px 48px rgb(34 62 91 / 9%);
}

.account-heading {
  margin-bottom: 28px;
  text-align: center;
}

.account-mark {
  display: grid;
  width: 52px;
  height: 52px;
  margin: 0 auto 16px;
  place-items: center;
  border-radius: 15px;
  background: #edf3f9;
  color: #3a6ea5;
  font-size: 23px;
}

.account-eyebrow {
  margin: 0 0 6px;
  color: #3a6ea5;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.1em;
}

.account-heading h1 {
  margin: 0;
  color: #24364b;
  font-size: 27px;
}

.account-description {
  margin: 10px 0 0;
  color: #718096;
}

.account-submit {
  width: 100%;
  margin-top: 6px;
}

.submit-icon {
  margin-left: 8px;
}

@media (max-width: 480px) {
  .account-page {
    padding-top: 32px;
  }

  .account-card {
    padding: 28px 22px;
  }
}
</style>
