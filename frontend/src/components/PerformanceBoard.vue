<template>
  <div>
    <div class="filter-bar">
      <el-select v-model="selectedProjectId" placeholder="选择项目" size="small" style="width:200px;" @change="loadCached" :loading="loadingProjects">
        <el-option v-for="p in projects" :key="p.id" :label="p.name" :value="p.id" />
      </el-select>
      <el-date-picker v-model="selectedDate" type="date" placeholder="选择日期" size="small" style="width:150px;"
        value-format="YYYY-MM-DD" @change="loadCached" />
      <div style="flex:1;" />
      <el-button size="small" type="primary" @click="handleFetch" :loading="fetching">
        <el-icon><Refresh /></el-icon> 拉取数据
      </el-button>
      <span v-if="lastFetchTime" style="font-size:12px;color:#909399;">上次拉取: {{ lastFetchTime }}</span>
    </div>
    <div class="table-wrap">
      <el-table :data="records" border size="small" style="width:100%;" v-loading="loading" max-height="70vh"
        @sort-change="handleSort" :default-sort="{ prop: 'acceptanceNum', order: 'descending' }">
        <el-table-column prop="userName" label="用户名" width="120" sortable="custom" fixed />
        <el-table-column prop="nickname" label="昵称" width="120" sortable="custom" />
        <el-table-column prop="labelNum" label="标注量" width="100" sortable="custom">
          <template #default="{ row }">
            <span style="color:#409EFF;font-weight:600;">{{ row.labelNum }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="reviewNum" label="审核量" width="100" sortable="custom">
          <template #default="{ row }">
            <span style="color:#E6A23C;font-weight:600;">{{ row.reviewNum }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="qualityNum" label="质检量" width="100" sortable="custom">
          <template #default="{ row }">
            <span style="color:#67C23A;font-weight:600;">{{ row.qualityNum }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="acceptanceNum" label="验收量" width="100" sortable="custom">
          <template #default="{ row }">
            <span style="color:#F56C6C;font-weight:600;">{{ row.acceptanceNum }}</span>
          </template>
        </el-table-column>
        <el-table-column label="合计" width="100" sortable="custom" prop="total">
          <template #default="{ row }">
            <span style="color:#303133;font-weight:700;">{{ row.labelNum + row.reviewNum + row.qualityNum + row.acceptanceNum }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!records.length && !loading" style="text-align:center;padding:40px;color:#909399;">
        请选择项目并点击「拉取数据」
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchProjects } from '../api/index.js'
import { getPerformance, fetchPerformance } from '../api/index.js'

const props = defineProps({ platformId: Number, platformName: String })

const projects = ref([])
const loadingProjects = ref(false)
const selectedProjectId = ref(null)
const selectedDate = ref('')
const records = ref([])
const loading = ref(false)
const fetching = ref(false)
const lastFetchTime = ref('')

function makeDateStr(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

async function loadProjects() {
  if (!props.platformId) return
  loadingProjects.value = true
  try {
    const res = await fetchProjects(props.platformId)
    projects.value = res.data
  } catch { /* ignore */ }
  finally { loadingProjects.value = false }
}

async function loadCached() {
  if (!selectedProjectId.value || !selectedDate.value) {
    records.value = []
    return
  }
  loading.value = true
  try {
    const res = await getPerformance(props.platformId, selectedProjectId.value, selectedDate.value)
    records.value = res.data
  } catch {
    records.value = []
  }
  finally { loading.value = false }
}

async function handleFetch() {
  if (!selectedProjectId.value) { ElMessage.warning('请选择项目'); return }
  if (!selectedDate.value) { ElMessage.warning('请选择日期'); return }
  fetching.value = true
  try {
    const res = await fetchPerformance({
      platformId: props.platformId,
      projectId: selectedProjectId.value,
      date: selectedDate.value,
    })
    ElMessage.success(res.data.message)
    lastFetchTime.value = new Date().toLocaleString('zh-CN')
    loadCached()
  } catch (e) {
    ElMessage.error('拉取失败: ' + (e.response?.data?.detail || e.message))
  }
  finally { fetching.value = false }
}

function handleSort({ prop, order }) {
  if (!prop || !order) return
  const dir = order === 'ascending' ? 1 : -1
  records.value.sort((a, b) => {
    let va, vb
    if (prop === 'total') {
      va = a.labelNum + a.reviewNum + a.qualityNum + a.acceptanceNum
      vb = b.labelNum + b.reviewNum + b.qualityNum + b.acceptanceNum
    } else {
      va = a[prop]
      vb = b[prop]
    }
    if (typeof va === 'string') return va.localeCompare(vb) * dir
    return (va - vb) * dir
  })
}

onMounted(() => {
  loadProjects()
  // Default to today
  selectedDate.value = makeDateStr(new Date())
})
</script>

<style scoped>
.filter-bar {
  background: #fff; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.table-wrap {
  background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
</style>
