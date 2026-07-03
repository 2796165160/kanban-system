<template>
  <div>
    <div class="list-header">
      <h2>标注平台</h2>
      <el-button type="primary" size="small" @click="showCreate = true">
        <el-icon><Plus /></el-icon> 新建平台
      </el-button>
    </div>
    <div v-if="loading" style="text-align:center;padding:40px;color:#909399;">加载中...</div>
    <div v-else-if="list.length === 0" style="text-align:center;padding:60px;color:#c0c4cc;">
      <el-icon :size="48"><FolderOpened /></el-icon>
      <p style="margin-top:12px;">暂无平台，请先新建</p>
    </div>
    <div v-else class="card-grid">
      <div v-for="p in list" :key="p.id" class="card-item" @click="$emit('select', p)">
        <div class="card-body">
          <el-icon :size="28" style="color:#409EFF;"><Monitor /></el-icon>
          <div class="card-name">{{ p.name }}</div>
        </div>
        <div class="card-actions" @click.stop>
          <el-button v-if="user?.role === 'admin'" size="small" text @click="openConnection(p)">配置</el-button>
          <el-button v-if="user?.role === 'admin'" size="small" text type="danger" @click="handleDelete(p)">删除</el-button>
        </div>
      </div>
    </div>
    <el-dialog v-model="showCreate" title="新建平台" width="360px">
      <el-input v-model="newName" placeholder="输入平台名称" @keyup.enter="handleCreate" />
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
    <ConnectionDialog ref="connectionDlg" :platform="currentPlatform" @saved="load" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchPlatforms, createPlatform, deletePlatform } from '../api/index.js'
import ConnectionDialog from './ConnectionDialog.vue'

const props = defineProps({ user: Object })
const emit = defineEmits(['select'])
const list = ref([])
const loading = ref(false)
const showCreate = ref(false)
const newName = ref('')
const connectionDlg = ref(null)
const currentPlatform = ref(null)

function openConnection(p) {
  currentPlatform.value = p
  connectionDlg.value?.open()
}

async function load() {
  loading.value = true
  try {
    const res = await fetchPlatforms()
    list.value = res.data
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}
async function handleCreate() {
  const name = newName.value.trim()
  if (!name) { ElMessage.warning('请输入名称'); return }
  try {
    await createPlatform(name)
    newName.value = ''
    showCreate.value = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}
async function handleDelete(p) {
  try {
    await ElMessageBox.confirm(`确定删除平台「${p.name}」？其下所有项目及数据将一并删除。`, '确认', { type: 'warning' })
    await deletePlatform(p.id)
    ElMessage.success('已删除')
    load()
  } catch { /* cancelled */ }
}
onMounted(load)
</script>

<style scoped>
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.list-header h2 { font-size: 18px; font-weight: 600; color: #303133; }
.card-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 16px; }
.card-item {
  background: #fff; border-radius: 10px; box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  cursor: pointer; transition: all 0.2s; overflow: hidden;
}
.card-item:hover { transform: translateY(-3px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
.card-body { padding: 28px 20px 12px; text-align: center; }
.card-name { margin-top: 10px; font-size: 16px; font-weight: 500; color: #303133; }
.card-actions { padding: 8px 12px; border-top: 1px solid #f0f0f0; text-align: right; }
</style>
