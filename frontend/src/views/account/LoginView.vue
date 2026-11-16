<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoute, useRouter } from 'vue-router'
import { ArrowRight, Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/modules/auth'
import { getAuthErrorMessage } from '@/utils/authError'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()
const loading = ref(false)
const form = ref({ identifier: '', password: '' })
const rules = {
  identifier: [{ required: true, message: t('auth_identifier_required'), trigger: 'blur' }],
  password: [{ required: true, message: t('auth_password_required'), trigger: 'blur' }]
}

async function submit() {
  if (loading.value) return

  loading.value = true
  try {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return

    await authStore.login(form.value.identifier, form.value.password)
    await router.replace(authStore.isAdmin ? '/account/admin' : '/account')
  } catch (error) {
    ElMessage.error(getAuthErrorMessage(error, t('auth_login_failed')))
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
        <h1>{{ t('auth_login_title') }}</h1>
        <p class="account-description">{{ t('auth_login_description') }}</p>
      </div>

      <el-alert
        v-if="route.query.session === 'check-failed'"
        :title="t('auth_session_check_failed')"
        type="warning"
        :closable="false"
        show-icon
        class="account-alert"
      />

      <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent="submit">
        <el-form-item prop="identifier">
          <el-input
            v-model="form.identifier"
            :placeholder="t('auth_identifier')"
            size="large"
            autocomplete="username"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            :placeholder="t('auth_password')"
            size="large"
            type="password"
            autocomplete="current-password"
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
          {{ t('auth_login_button') }}
          <el-icon class="submit-icon"><ArrowRight /></el-icon>
        </el-button>
      </el-form>

      <p class="forgot-link">
        <router-link to="/forgot-password">{{ t('auth_forgot_password_link') }}</router-link>
      </p>
      <p class="account-switch">
        {{ t('auth_no_account') }}
        <router-link to="/register">{{ t('auth_register_link') }}</router-link>
      </p>
      <p class="account-note">{{ t('auth_admin_note') }}</p>
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

.account-alert {
  margin-bottom: 18px;
}

.account-submit {
  width: 100%;
  margin-top: 6px;
}

.submit-icon {
  margin-left: 8px;
}

.account-switch,
.forgot-link,
.account-note {
  margin: 20px 0 0;
  color: #66788a;
  text-align: center;
}

.account-switch a,
.forgot-link a {
  color: #3a6ea5;
  font-weight: 600;
  text-decoration: none;
}

.account-note {
  margin-top: 12px;
  color: #8a97a6;
  font-size: 13px;
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
