<template>
  <Login v-if="!user" @login-success="onLogin" />
  <el-container v-else style="min-height:100vh;">
    <el-header class="app-header">
      <h1><el-icon :size="24"><FolderOpened /></el-icon> 标注进度预览</h1>
      <div class="header-right">
        <template v-if="currentPlatform && user.role === 'admin'">
          <el-button size="small" text @click="goPerformance" :type="view === 'performance' ? 'primary' : 'default'">
            <el-icon><DataAnalysis /></el-icon> 绩效统计
          </el-button>
        </template>
        <template v-if="view === 'board' && user.role !== 'inspector'">
          <span class="location-label">{{ currentProject?.name }}</span>
          <el-upload :show-file-list="false" :before-upload="onUpload" accept=".csv">
            <el-button type="primary" plain style="color:rgba(0, 0, 0, 0.5);border-color:rgba(0, 0, 0, 0.5);">
              <el-icon><Upload /></el-icon> 上传CSV
            </el-button>
          </el-upload>
        </template>
        <el-dropdown trigger="click" @command="handleMenu">
          <span class="user-btn">
            <el-icon><User /></el-icon> {{ user.username }}
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="user.role === 'admin'" command="users">
                <el-icon><Setting /></el-icon> 用户管理
              </el-dropdown-item>
              <el-dropdown-item command="logout">
                <el-icon><SwitchButton /></el-icon> 退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <div class="breadcrumb-bar">
      <a class="crumb-link" @click="goPlatforms">标注平台</a>
      <span v-if="currentPlatform" class="crumb-sep"> › </span>
      <a v-if="currentPlatform && view !== 'projects'" class="crumb-link" @click="goProjects">{{ currentPlatform.name }}</a>
      <span v-else-if="currentPlatform" class="crumb-current">{{ currentPlatform.name }}</span>
      <span v-if="view === 'performance'" class="crumb-sep"> › </span>
      <span v-if="view === 'performance'" class="crumb-current">绩效统计</span>
      <span v-if="currentProject" class="crumb-sep"> › </span>
      <span v-if="currentProject" class="crumb-current">{{ currentProject.name }}</span>
    </div>
    <el-main class="main-content">
      <PlatformList
        v-if="view === 'platforms'"
        :user="user"
        @select="onSelectPlatform"
      />
      <ProjectList
        v-else-if="view === 'projects'"
        :platform-id="currentPlatform.id"
        :user="user"
        @select="onSelectProject"
      />
      <TaskBoard
        v-else-if="view === 'board'"
        :project-id="currentProject.id"
        :platform-id="currentPlatform.id"
        :user="user"
      />
      <PerformanceBoard
        v-else-if="view === 'performance' && user.role === 'admin'"
        :platform-id="currentPlatform.id"
        :platform-name="currentPlatform?.name"
      />
    </el-main>
    <UserManage ref="userManageRef" />
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { FolderOpened, User, ArrowDown, Upload, Setting, SwitchButton, DataAnalysis } from '@element-plus/icons-vue'
import { fetchMe, uploadCsv } from './api/index.js'
import Login from './views/Login.vue'
import PlatformList from './components/PlatformList.vue'
import ProjectList from './components/ProjectList.vue'
import TaskBoard from './components/TaskBoard.vue'
import UserManage from './components/UserManage.vue'
import PerformanceBoard from './components/PerformanceBoard.vue'

const user = ref(null)
const view = ref('platforms')
const currentPlatform = ref(null)
const currentProject = ref(null)
const userManageRef = ref(null)

function onLogin(u) {
  user.value = u
}

function handleMenu(cmd) {
  if (cmd === 'logout') {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    user.value = null
  } else if (cmd === 'users') {
    userManageRef.value?.open()
  }
}

function goPlatforms() {
  view.value = 'platforms'
  currentPlatform.value = null
  currentProject.value = null
}
function goProjects() {
  view.value = 'projects'
  currentProject.value = null
}
function onSelectPlatform(p) {
  currentPlatform.value = p
  view.value = 'projects'
}
function onSelectProject(p) {
  currentProject.value = p
  view.value = 'board'
}
function goPerformance() {
  view.value = 'performance'
  currentProject.value = null
}
async function onUpload(file) {
  try {
    const res = await uploadCsv(currentProject.value.id, file)
    ElMessage.success(res.data.message)
    window.__kanbanReload?.()
  } catch (e) {
    ElMessage.error('上传失败: ' + (e.response?.data?.detail || e.message))
  }
  return false
}

onMounted(async () => {
  const token = localStorage.getItem('token')
  const saved = localStorage.getItem('user')
  if (token && saved) {
    try {
      const me = await fetchMe()
      user.value = me.data
      localStorage.setItem('user', JSON.stringify(me.data))
    } catch {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    }
  }
})
</script>

<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: #f0f2f5; font-family: 'Microsoft YaHei', -apple-system, sans-serif; }
.app-header {
  background: linear-gradient(0deg, #56b3ffff, #56b3ffff);
  color: #fff; padding: 10px 24px; display: flex; align-items: center;
  justify-content: space-between; box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  position: sticky; top: 0; z-index: 100;
}
.app-header h1 { font-size: 20px; font-weight: 600; display: flex; align-items: center; gap: 10px; }
.header-right { display: flex; align-items: center; gap: 12px; }
.location-label { font-size: 13px; opacity: 0.85; }
.user-btn { cursor: pointer; display: flex; align-items: center; gap: 4px; font-size: 14px; }
.user-btn:hover { opacity: 0.8; }
.breadcrumb-bar {
  background: #fff; padding: 8px 24px; font-size: 14px;
  border-bottom: 1px solid #e4e7ed; display: flex; align-items: center; gap: 4px;
}
.crumb-link { color: #409EFF; cursor: pointer; }
.crumb-link:hover { color: #66b1ff; }
.crumb-sep { color: #c0c4cc; }
.crumb-current { color: #606266; }
.main-content { max-width: 1600px; margin: 0 auto; padding: 16px 20px; width: 100%; }
</style>
