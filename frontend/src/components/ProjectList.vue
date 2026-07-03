<template>
  <div>
    <div class="list-header">
      <h2>项目列表</h2>
      <el-button type="primary" size="small" @click="showCreate = true">
        <el-icon><Plus /></el-icon> 新建项目
      </el-button>
    </div>
    <div v-if="loading" style="text-align:center;padding:40px;color:#909399;">加载中...</div>
    <div v-else-if="list.length === 0" style="text-align:center;padding:60px;color:#c0c4cc;">
      <el-icon :size="48"><FolderOpened /></el-icon>
      <p style="margin-top:12px;">暂无项目，请先新建</p>
    </div>
    <div v-else class="card-grid">
      <div v-for="p in list" :key="p.id" class="card-item" @click="$emit('select', p)">
        <div class="card-body">
          <el-icon :size="28" style="color:#67C23A;"><List /></el-icon>
          <div class="card-name">{{ p.name }}</div>
          <div v-if="p.projectKey" class="card-key" @click.stop>key: {{ p.projectKey }}</div>
        </div>
        <div class="card-actions" @click.stop>
          <el-button v-if="user?.role === 'admin'" size="small" text @click="editProjectKey(p)">Key</el-button>
          <el-button v-if="user?.role === 'admin'" size="small" text type="primary" :loading="fetchingId === p.id" @click="handleFetch(p)">拉取</el-button>
          <el-button v-if="user?.role === 'admin'" size="small" text type="danger" @click="handleDelete(p)">删除</el-button>
        </div>
      </div>
    </div>
    <el-dialog v-model="showCreate" title="新建项目" width="380px">
      <el-form label-width="70px">
        <el-form-item label="项目名称">
          <el-input v-model="newName" placeholder="输入项目名称" @keyup.enter="handleCreate" />
        </el-form-item>
        <el-form-item label="项目 Key">
          <el-input v-model="newProjectKey" placeholder="如 pr_kqQ-88Tpl946V" @keyup.enter="handleCreate" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="handleCreate">确定</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="showKeyEdit" title="修改项目 Key" width="380px">
      <el-input v-model="editKeyValue" :placeholder="editKeyTarget?.projectKey || ''" />
      <template #footer>
        <el-button @click="showKeyEdit = false">取消</el-button>
        <el-button type="primary" @click="confirmKeyEdit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchProjects, createProject, updateProject, deleteProject, fetchProjectData } from '../api/index.js'

const props = defineProps({ platformId: Number, user: Object })
const emit = defineEmits(['select'])
const list = ref([])
const loading = ref(false)
const showCreate = ref(false)
const newName = ref('')
const newProjectKey = ref('')
const showKeyEdit = ref(false)
const editKeyTarget = ref(null)
const editKeyValue = ref('')
const fetchingId = ref(null)

async function load() {
  loading.value = true
  try {
    const res = await fetchProjects(props.platformId)
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
    await createProject(name, props.platformId, newProjectKey.value.trim())
    newName.value = ''
    newProjectKey.value = ''
    showCreate.value = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  }
}
function editProjectKey(p) {
  editKeyTarget.value = p
  editKeyValue.value = p.projectKey || ''
  showKeyEdit.value = true
}
async function handleFetch(p) {
  fetchingId.value = p.id
  try {
    const res = await fetchProjectData(props.platformId, p.id)
    if (res.data.results) {
      const ok = res.data.results.filter(r => r.status === 'ok').length
      const err = res.data.results.filter(r => r.status !== 'ok').length
      ElMessage.success(`${res.data.message}（成功${ok}，失败${err}）`)
    } else {
      ElMessage.success(res.data.message || '拉取完成')
    }
  } catch (e) {
    ElMessage.error('拉取失败: ' + (e.response?.data?.detail || e.message))
  } finally { fetchingId.value = null }
}

async function confirmKeyEdit() {
  if (!editKeyTarget.value) return
  try {
    await updateProject(editKeyTarget.value.id, { projectKey: editKeyValue.value.trim() })
    ElMessage.success('Key 已更新')
    showKeyEdit.value = false
    load()
  } catch (e) {
    ElMessage.error('更新失败')
  }
}
async function handleDelete(p) {
  try {
    await ElMessageBox.confirm(`确定删除项目「${p.name}」？其下所有任务及数据将一并删除。`, '确认', { type: 'warning' })
    await deleteProject(p.id)
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
.card-key { margin-top: 4px; font-size: 11px; color: #909399; word-break: break-all; }
.card-actions { padding: 8px 12px; border-top: 1px solid #f0f0f0; text-align: right; }
</style>
