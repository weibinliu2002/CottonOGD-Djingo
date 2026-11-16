<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { Lock, Setting, SwitchButton } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/modules/auth'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()

function logout() {
  authStore.logout()
  router.replace('/login')
}
</script>

<template>
  <section class="dashboard admin-dashboard">
    <div class="dashboard-heading">
      <div>
        <p class="dashboard-eyebrow">{{ t('auth_admin_area') }}</p>
        <h1>{{ t('auth_welcome_admin', { name: authStore.user?.username }) }}</h1>
      </div>
      <el-button plain @click="logout">
        <el-icon><SwitchButton /></el-icon>
        {{ t('auth_logout') }}
      </el-button>
    </div>

    <el-card class="admin-card" shadow="never">
      <div class="admin-icon"><el-icon><Setting /></el-icon></div>
      <div class="admin-content">
        <span class="admin-badge"><el-icon><Lock /></el-icon>{{ t('auth_admin_badge') }}</span>
        <h2>{{ t('auth_admin_dashboard_title') }}</h2>
        <p>{{ t('auth_admin_dashboard_description') }}</p>
        <dl>
          <div>
            <dt>{{ t('auth_username') }}</dt>
            <dd>{{ authStore.user?.username }}</dd>
          </div>
          <div>
            <dt>{{ t('auth_email') }}</dt>
            <dd>{{ authStore.user?.email }}</dd>
          </div>
        </dl>
      </div>
    </el-card>
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

.admin-card {
  overflow: hidden;
  border: 1px solid #dfe8f1;
  border-radius: 14px;
  background: linear-gradient(135deg, #f8fbff, #fff 70%);
}

.admin-card :deep(.el-card__body) {
  display: flex;
  gap: 24px;
  padding: 32px;
}

.admin-icon {
  display: grid;
  flex: 0 0 60px;
  width: 60px;
  height: 60px;
  place-items: center;
  border-radius: 17px;
  background: #3a6ea5;
  color: #fff;
  font-size: 28px;
}

.admin-content {
  min-width: 0;
}

.admin-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border-radius: 999px;
  background: #e8f0f8;
  color: #315e8d;
  font-size: 12px;
  font-weight: 700;
}

.admin-content h2 {
  margin: 16px 0 8px;
  color: #24364b;
  font-size: 22px;
}

.admin-content p {
  max-width: 620px;
  margin: 0;
  color: #66788a;
  line-height: 1.7;
}

.admin-content dl {
  display: flex;
  flex-wrap: wrap;
  gap: 18px 40px;
  margin: 24px 0 0;
}

.admin-content dt {
  margin-bottom: 5px;
  color: #7a8795;
  font-size: 13px;
}

.admin-content dd {
  overflow-wrap: anywhere;
  margin: 0;
  color: #27394e;
  font-weight: 600;
}

@media (max-width: 600px) {
  .dashboard {
    padding-top: 32px;
  }

  .dashboard-heading {
    align-items: flex-start;
  }

  .admin-card :deep(.el-card__body) {
    flex-direction: column;
    padding: 24px;
  }
}
</style>
