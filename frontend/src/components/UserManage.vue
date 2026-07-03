<template>
  <el-dialog v-model="visible" title="用户管理" width="500px" :close-on-click-modal="false">
    <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap;">
      <el-input v-model="newUsername" placeholder="用户名" size="small" style="width:140px;" />
      <el-input v-model="newPassword" type="password" placeholder="密码" size="small" style="width:130px;" show-password />
      <el-select v-model="newRole" size="small" style="width:110px;">
        <el-option label="普通用户" value="user" />
        <el-option label="管理员" value="admin" />
        <el-option label="验收员" value="inspector" />
      </el-select>
      <el-button type="primary" size="small" @click="handleCreate">新建</el-button>
    </div>
    <el-table :data="users" size="small" border style="width:100%;">
      <el-table-column prop="username" label="用户名" min-width="120" />
      <el-table-column prop="role" label="角色" width="90">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : row.role === 'inspector' ? 'warning' : 'info'" size="small">
            {{ row.role === 'admin' ? '管理员' : row.role === 'inspector' ? '验收员' : '普通用户' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="createdAt" label="创建时间" min-width="140" />
      <el-table-column label="操作" width="80">
        <template #default="{ row }">
          <el-button size="small" text type="danger" :disabled="row.role === 'admin'" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchUsers, createUser, deleteUser } from '../api/index.js'

const visible = ref(false)
const users = ref([])
const newUsername = ref('')
const newPassword = ref('')
const newRole = ref('user')

async function load() {
  try {
    const res = await fetchUsers()
    users.value = res.data
  } catch { /* ignore */ }
}

async function handleCreate() {
  const name = newUsername.value.trim()
  const pwd = newPassword.value.trim()
  if (!name || !pwd) { ElMessage.warning('请输入用户名和密码'); return }
  try {
    await createUser(name, pwd, newRole.value)
    ElMessage.success('创建成功')
    newUsername.value = ''
    newPassword.value = ''
    newRole.value = 'user'
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除用户「${row.username}」？`, '确认', { type: 'warning' })
    await deleteUser(row.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}

function open() {
  visible.value = true
  load()
}

defineExpose({ open })
</script>
