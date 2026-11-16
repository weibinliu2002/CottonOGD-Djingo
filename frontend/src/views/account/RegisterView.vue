<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { ArrowRight, Lock, Message, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/modules/auth'
import { getAuthErrorMessage } from '@/utils/authError'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const formRef = ref()
const loading = ref(false)
const submitted = ref(false)
const form = ref({ username: '', email: '', password: '', confirmPassword: '' })
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
  username: [{ required: true, message: t('auth_username_required'), trigger: 'blur' }],
  email: [
    { required: true, message: t('auth_email_required'), trigger: 'blur' },
    { type: 'email', message: t('auth_email_invalid'), trigger: 'blur' }
  ],
  password: [{ validator: validatePassword, trigger: 'blur' }],
  confirmPassword: [{ validator: validateConfirmPassword, trigger: 'blur' }]
}

async function submit() {
  if (loading.value || submitted.value) return

  loading.value = true
  try {
    const valid = await formRef.value?.validate().catch(() => false)
    if (!valid) return

    await authStore.register(
      form.value.username,
      form.value.email,
      form.value.password,
      form.value.confirmPassword
    )
    submitted.value = true
  } catch (error) {
    ElMessage.error(getAuthErrorMessage(error, t('auth_register_failed')))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <section class="account-page">
    <div class="account-card">
      <div class="account-heading">
        <div class="account-mark"><User /></div>
        <p class="account-eyebrow">iCotton</p>
        <h1>{{ submitted ? t('auth_check_email_title') : t('auth_register_title') }}</h1>
        <p class="account-description">
          {{ submitted ? t('auth_check_email_description') : t('auth_register_description') }}
        </p>
      </div>

      <template v-if="submitted">
        <el-result icon="success" :title="t('auth_registration_complete')" />
        <el-button type="primary" size="large" class="account-submit" @click="router.push('/login')">
          {{ t('auth_back_to_login') }}
        </el-button>
      </template>

      <el-form v-else ref="formRef" :model="form" :rules="rules" @submit.prevent="submit">
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            :placeholder="t('auth_username')"
            size="large"
            autocomplete="username"
            :prefix-icon="User"
          />
        </el-form-item>
        <el-form-item prop="email">
          <el-input
            v-model="form.email"
            :placeholder="t('auth_email')"
            size="large"
            autocomplete="email"
            :prefix-icon="Message"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            :placeholder="t('auth_password')"
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
          {{ t('auth_register_button') }}
          <el-icon class="submit-icon"><ArrowRight /></el-icon>
        </el-button>
      </el-form>

      <p v-if="!submitted" class="account-switch">
        {{ t('auth_have_account') }}
        <router-link to="/login">{{ t('auth_login_link') }}</router-link>
      </p>
      <p class="account-note">{{ t('auth_admin_registration_note') }}</p>
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
  width: min(100%, 460px);
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

.account-switch,
.account-note {
  margin: 20px 0 0;
  color: #66788a;
  text-align: center;
}

.account-switch a {
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
