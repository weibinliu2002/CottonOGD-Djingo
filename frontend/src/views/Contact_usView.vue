<template>
  <div class="container mt-4">
    <div class="page-header">
      <h1 class="page-title">{{ t('contact_us') }}</h1>
      <p class="page-description">{{ t('get_in_touch') }}</p>
    </div>
    <el-card>
      <h4>Github issues:<a href="https://github.com/weibinliu2002/CottonOGD-Djingo/issues" target="_blank">weibinliu</a></h4>
      <h4>Google Email:<a href="liuweibin2002@gmail.com">liuweibin2002@gmail.com</a></h4>
      <h4>163 Email:<a href="liuweibin2002@163.com">liuweibin2002@163.com</a></h4>
    </el-card>
    
    <!-- 回到顶部 -->
    <el-backtop :right="40" :bottom="40" />
  </div>
</template>

<script>
import { useI18n } from 'vue-i18n'

export default {
  name: 'Contact_usView',
  setup() {
    const { t } = useI18n()
    return {
      t
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  text-align: left;
  margin-bottom: 30px;
}

.page-title {
  font-size: 36px;
  font-weight: 600;
  color: #3a6ea5;
  margin-bottom: 16px;
}

.page-description {
  font-size: 16px;
  color: #666;
  line-height: 1.6;
  max-width: 800px;
  margin: 0;
}
</style>