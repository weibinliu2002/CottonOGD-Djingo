<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Avatar, CircleCheck, Delete, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/modules/auth'
import { getAuthErrorMessage } from '@/utils/authError'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const deleteDialogVisible = ref(false)
const deleteConfirmation = ref('')
const deleting = ref(false)
const deleteConfirmationKeyword = 'DELETE'
const canDeleteAccount = computed(() => deleteConfirmation.value === deleteConfirmationKeyword)

function logout() {
  authStore.logout()
  router.replace('/login')
}

async function deleteAccount() {
  if (deleting.value || !canDeleteAccount.value || authStore.isAdmin) return

  deleting.value = true
  try {
    await authStore.deleteAccount()
    deleteDialogVisible.value = false
    ElMessage.success(t('auth_delete_account_success'))
    await router.replace('/')
  } catch (error) {
    ElMessage.error(getAuthErrorMessage(error, t('auth_delete_account_failed')))
  } finally {
    deleting.value = false
  }
}
</script>

<template>
  <section class="dashboard">
    <div class="dashboard-heading">
      <div>
        <p class="dashboard-eyebrow">{{ t('auth_user_area') }}</p>
        <h1>{{ t('auth_welcome_user', { name: authStore.user?.username }) }}</h1>
      </div>
      <el-button plain @click="logout">
        <el-icon><SwitchButton /></el-icon>
        {{ t('auth_logout') }}
      </el-button>
    </div>

    <el-card class="profile-card" shadow="never">
      <div class="profile-icon"><el-icon><Avatar /></el-icon></div>
      <div class="profile-info">
        <h2>{{ t('auth_account_information') }}</h2>
        <dl>
          <div>
            <dt>{{ t('auth_username') }}</dt>
            <dd>{{ authStore.user?.username }}</dd>
          </div>
          <div>
            <dt>{{ t('auth_email') }}</dt>
            <dd class="email-value">
              {{ authStore.user?.email }}
              <span v-if="authStore.user?.email_verified" class="verified">
                <el-icon><CircleCheck /></el-icon>
                {{ t('auth_email_verified') }}
              </span>
            </dd>
          </div>
          <div v-if="authStore.user?.id !== undefined">
            <dt>{{ t('auth_account_id') }}</dt>
            <dd>{{ authStore.user.id }}</dd>
          </div>
        </dl>
      </div>
    </el-card>

    <el-alert
      :title="t('auth_user_dashboard_note')"
      type="info"
      :closable="false"
      show-icon
      class="dashboard-note"
    />

    <el-card v-if="!authStore.isAdmin" class="danger-card" shadow="never">
      <div>
        <h2>{{ t('auth_delete_account') }}</h2>
        <p>{{ t('auth_delete_account_description') }}</p>
      </div>
      <el-button type="danger" plain @click="deleteDialogVisible = true">
        <el-icon><Delete /></el-icon>
        {{ t('auth_delete_account') }}
      </el-button>
    </el-card>

    <el-dialog
      v-model="deleteDialogVisible"
      :title="t('auth_delete_account_dialog_title')"
      width="min(92vw, 460px)"
      @closed="deleteConfirmation = ''"
    >
      <el-alert
        :title="t('auth_delete_account_warning')"
        type="error"
        :closable="false"
        show-icon
      />
      <el-form class="delete-confirmation">
        <el-form-item :label="t('auth_delete_account_confirmation_label', { keyword: deleteConfirmationKeyword })">
          <el-input
            v-model="deleteConfirmation"
            :placeholder="deleteConfirmationKeyword"
            autocomplete="off"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button :disabled="deleting" @click="deleteDialogVisible = false">
          {{ t('auth_cancel') }}
        </el-button>
        <el-button
          type="danger"
          :disabled="!canDeleteAccount"
          :loading="deleting"
          @click="deleteAccount"
        >
          {{ t('auth_delete_account_confirm_button') }}
        </el-button>
      </template>
    </el-dialog>
  </section>
</template>

<style scoped>
.dashboard {
  max-width: 920px;
  min-height: 430px;
  margin: 0 auto;
  padding: 48px 16px 72px;
}

.dashboard-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 28px;
}

.dashboard-eyebrow {
  margin: 0 0 8px;
  color: #3a6ea5;
  font-size: 13px;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
}

.dashboard-heading h1 {
  margin: 0;
  color: #24364b;
  font-size: clamp(24px, 4vw, 32px);
}

.profile-card {
  border-radius: 14px;
}

.profile-card :deep(.el-card__body) {
  display: flex;
  gap: 22px;
  padding: 28px;
}

.profile-icon {
  display: grid;
  flex: 0 0 56px;
  width: 56px;
  height: 56px;
  place-items: center;
  border-radius: 16px;
  background: #edf3f9;
  color: #3a6ea5;
  font-size: 27px;
}

.profile-info {
  flex: 1;
  min-width: 0;
}

.profile-info h2 {
  margin: 2px 0 18px;
  color: #2d4056;
  font-size: 20px;
}

.profile-info dl {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 28px;
  margin: 0;
}

.profile-info dt {
  margin-bottom: 5px;
  color: #7a8795;
  font-size: 13px;
}

.profile-info dd {
  overflow-wrap: anywhere;
  margin: 0;
  color: #27394e;
  font-weight: 600;
}

.email-value,
.verified {
  display: flex;
  align-items: center;
  gap: 7px;
}

.verified {
  color: #39845d;
  font-size: 12px;
  font-weight: 500;
}

.dashboard-note {
  margin-top: 20px;
}

.danger-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-top: 32px;
  border-color: #f0caca;
}

.danger-card :deep(.el-card__body) {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  width: 100%;
}

.danger-card h2 {
  margin: 0 0 6px;
  color: #8d3434;
  font-size: 17px;
}

.danger-card p {
  margin: 0;
  color: #7a6262;
  line-height: 1.5;
}

.delete-confirmation {
  margin-top: 20px;
}

@media (max-width: 600px) {
  .dashboard {
    padding-top: 32px;
  }

  .dashboard-heading {
    align-items: flex-start;
  }

  .profile-card :deep(.el-card__body) {
    flex-direction: column;
    padding: 22px;
  }

  .profile-info dl {
    grid-template-columns: minmax(0, 1fr);
  }

  .danger-card :deep(.el-card__body) {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
