<template>
  <div class="login-wrapper">
    <div class="login-container">
      <div class="login-brand">
        <div class="brand-content">
          <div class="brand-icon">
            <el-icon :size="48"><DataBoard /></el-icon>
          </div>
          <h1>标注进度预览</h1>
          <p class="brand-desc">数据标注全流程管理平台</p>
          <div class="brand-features">
            <div class="feature-item"><el-icon><CircleCheck /></el-icon> 多平台多项目管理</div>
            <div class="feature-item"><el-icon><CircleCheck /></el-icon> 四道工序状态追踪</div>
            <div class="feature-item"><el-icon><CircleCheck /></el-icon> 导出 / 回传全记录</div>
          </div>
        </div>
      </div>
      <div class="login-form-panel">
        <div class="form-header">
          <h2>欢迎登录</h2>
          <p class="form-desc">请使用账号密码登录系统</p>
        </div>
        <el-form @submit.prevent="handleLogin" class="login-form">
          <el-form-item>
            <el-input v-model="username" placeholder="用户名" size="large" :prefix-icon="User" @keyup.enter="handleLogin" />
          </el-form-item>
          <el-form-item>
            <el-input v-model="password" type="password" placeholder="密码" size="large" :prefix-icon="Lock" show-password @keyup.enter="handleLogin" />
          </el-form-item>
          <el-button type="primary" size="large" class="login-btn" :loading="loading" @click="handleLogin">
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form>
        <p v-if="error" class="login-error"><el-icon><WarningFilled /></el-icon> {{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { login } from '../api/index.js'

const emit = defineEmits(['login-success'])
const username = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await login(username.value.trim(), password.value)
    localStorage.setItem('token', res.data.token)
    localStorage.setItem('user', JSON.stringify(res.data.user))
    emit('login-success', res.data.user)
  } catch (e) {
    error.value = e.response?.data?.detail || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrapper {
  min-height: 100vh;
  background: #f0f2f5;
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.login-container {
  display: flex;
  width: 880px; max-width: 100%;
  min-height: 520px;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 12px 48px rgba(0,0,0,0.12);
}
.login-brand {
  flex: 1.2;
  background: linear-gradient(145deg, #1a1a2e, #16213e, #0f3460);
  color: #fff;
  display: flex; align-items: center; justify-content: center;
  padding: 48px 40px;
  position: relative;
  overflow: hidden;
}
.login-brand::before {
  content: '';
  position: absolute;
  top: -50%; left: -50%;
  width: 200%; height: 200%;
  background: radial-gradient(circle at 30% 40%, rgba(99,179,237,0.08) 0%, transparent 60%);
}
.brand-content { position: relative; z-index: 1; }
.brand-icon { margin-bottom: 20px; }
.brand-icon .el-icon { color: #64b5f6; }
.brand-content h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px; letter-spacing: 1px; }
.brand-desc { font-size: 15px; color: rgba(255,255,255,0.6); margin-bottom: 36px; }
.brand-features { display: flex; flex-direction: column; gap: 14px; }
.feature-item {
  display: flex; align-items: center; gap: 10px;
  font-size: 14px; color: rgba(255,255,255,0.8);
}
.feature-item .el-icon { color: #81c784; font-size: 16px; }

.login-form-panel {
  flex: 1;
  background: #fff;
  display: flex; flex-direction: column;
  justify-content: center;
  padding: 48px 44px;
}
.form-header { margin-bottom: 32px; }
.form-header h2 { font-size: 24px; font-weight: 600; color: #1a1a2e; margin-bottom: 6px; }
.form-desc { font-size: 14px; color: #909399; }
.login-form { width: 100%; }
.login-form :deep(.el-form-item) { margin-bottom: 20px; }
.login-btn { width: 100%; height: 44px; font-size: 15px; border-radius: 8px; margin-top: 4px; }
.login-error {
  color: #F56C6C; font-size: 13px; margin-top: 16px;
  display: flex; align-items: center; gap: 4px; justify-content: center;
}
</style>
