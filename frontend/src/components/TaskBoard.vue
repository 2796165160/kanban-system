<template>
  <div>
    <StatsCards :stats="stats" :user="user" v-if="stats.totalItems > 0" style="margin-bottom:16px;" />
    <div class="filter-bar">
      <el-input v-model="search" placeholder="搜索任务名称" clearable size="small" style="width:180px;">
        <template #prefix><el-icon><Search /></el-icon></template>
      </el-input>
      <el-select v-model="filterProcess" placeholder="工序" clearable size="small" style="width:120px;">
        <el-option v-if="!isInspector" label="标注" value="labelStatus" />
        <el-option v-if="!isInspector" label="审核" value="reviewStatus" />
        <el-option label="质检" value="qualityStatus" />
        <el-option label="验收" value="acceptanceStatus" />
      </el-select>
      <el-select v-model="filterStatus" placeholder="状态" clearable size="small" style="width:110px;" :disabled="!filterProcess">
        <el-option v-for="s in statusOptions" :key="s" :label="s" :value="s" />
      </el-select>
      <div style="flex:1;" />
      <el-button size="small" @click="snapshotDlg?.open()">
        <el-icon><Clock /></el-icon> 快照历史
      </el-button>
      <el-button v-if="!isInspector" size="small" type="success" @click="downloadCsv">
        <el-icon><Download /></el-icon> 导出CSV
      </el-button>
      <el-upload v-if="!isInspector" :show-file-list="false" :before-upload="handleExportCsvUpload" accept=".csv">
        <el-button size="small" type="warning">
          <el-icon><Upload /></el-icon> 导入导出统计
        </el-button>
      </el-upload>
      <el-button v-if="!isInspector" size="small" type="primary" plain @click="filterPendingExport">
        <el-icon><Filter /></el-icon> 筛选待导出
      </el-button>
    </div>
    <div class="table-wrap">
      <el-table :data="tasks" style="width:100%" row-key="taskName" border size="small" v-loading="loading">
        <el-table-column type="expand" width="34">
          <template #default="{ row }">
            <div style="padding:8px;">
              <div v-if="row._selectedItems?.length" class="batch-bar">
                <span style="font-size:13px;color:#606266;">已选 <b>{{ row._selectedItems.length }}</b> 条</span>
                <template v-if="!isInspector">
                  <el-select v-model="batchField" placeholder="字段" size="small" style="width:110px;" @change="onBatchFieldChange">
                    <el-option label="标注" value="labelStatus" />
                    <el-option label="审核" value="reviewStatus" />
                    <el-option label="质检" value="qualityStatus" />
                    <el-option label="验收" value="acceptanceStatus" />
                    <el-option label="导出" value="exportStatus" />
                    <el-option label="回传" value="returnStatus" />
                  </el-select>
                  <el-select v-model="batchValue" placeholder="值" size="small" style="width:110px;">
                    <el-option v-for="s in batchOptions" :key="s" :label="s" :value="s" />
                  </el-select>
                  <el-button size="small" type="primary" :disabled="!batchField || !batchValue" @click="doBatch(row)">
                    批量修改
                  </el-button>
                  <el-button size="small" type="success" :disabled="!row._selectedItems?.length" @click="exportSelected(row)">
                    <el-icon><Download /></el-icon> 导出原文件
                  </el-button>
                </template>
              </div>
              <el-table :data="row.details" size="small" border @selection-change="(sel) => row._selectedItems = sel">
                <el-table-column v-if="!isInspector" type="selection" width="32" />
                <el-table-column prop="questionId" label="题ID" width="70" />
                <el-table-column label="序列名称" min-width="180">
                  <template #default="{ row: d }">
                    <span :title="d.clipName">{{ d.clipName }}</span>
                  </template>
                </el-table-column>
                <el-table-column v-if="!isInspector" label="标注" width="110">
                  <template #default="{ row: d }">
                    <EditableStatus :status="d.labelStatus" field="labelStatus" @change="changeStatus(d, $event)" />
                  </template>
                </el-table-column>
                <el-table-column v-if="!isInspector" label="审核" width="110">
                  <template #default="{ row: d }">
                    <EditableStatus :status="d.reviewStatus" field="reviewStatus" @change="changeStatus(d, $event)" />
                  </template>
                </el-table-column>
                <el-table-column label="质检" width="110">
                  <template #default="{ row: d }">
                    <EditableStatus :status="d.qualityStatus" field="qualityStatus" :disabled="isInspector" @change="changeStatus(d, $event)" />
                  </template>
                </el-table-column>
                <el-table-column label="验收" width="110">
                  <template #default="{ row: d }">
                    <EditableStatus :status="d.acceptanceStatus" field="acceptanceStatus" :disabled="isInspector" @change="changeStatus(d, $event)" />
                  </template>
                </el-table-column>
                <el-table-column label="导出" width="80">
                  <template #default="{ row: d }">
                    <EditableStatus :status="d.exportStatus || '未导出'" :options="exportOptions" field="exportStatus" @change="changeStatus(d, $event)" />
                  </template>
                </el-table-column>
                <el-table-column label="导出日期" width="110">
                  <template #default="{ row: d }">
                    <EditableDate
                      v-if="d.exportStatus === '已导出'"
                      :date="d.exportDate"
                      @change="changeDate(d, 'exportDate', $event)"
                    />
                    <span v-else style="color:#c0c4cc;">-</span>
                  </template>
                </el-table-column>
                <el-table-column label="回传" width="80">
                  <template #default="{ row: d }">
                    <EditableStatus :status="d.returnStatus || '未回传'" :options="returnOptions" field="returnStatus" @change="changeStatus(d, $event)" />
                  </template>
                </el-table-column>
                <el-table-column label="回传日期" width="110">
                  <template #default="{ row: d }">
                    <EditableDate
                      v-if="d.returnStatus === '已回传'"
                      :date="d.returnDate"
                      @change="changeDate(d, 'returnDate', $event)"
                    />
                    <span v-else style="color:#c0c4cc;">-</span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="taskName" label="任务名称" min-width="160" show-overflow-tooltip sortable />
        <el-table-column label="Key" width="120">
          <template #default="{ row }">
            <span v-if="row.taskKey" class="task-key" @click="editTaskKey(row)" :title="'点击修改'">{{ row.taskKey }}</span>
            <span v-else class="task-key-empty" @click="editTaskKey(row)">+ 设置 Key</span>
          </template>
        </el-table-column>
        <el-table-column label="总题" width="55" align="center" sortable>
          <template #default="{ row }">{{ row.details.length }}</template>
        </el-table-column>
        <el-table-column label="标注" width="55" align="center" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.labelPassed === row.details.length ? '#67C23A' : undefined, fontWeight: 600 }">{{ row.labelPassed }}</span>
          </template>
        </el-table-column>
        <el-table-column label="审核" width="55" align="center" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.reviewPassed === row.details.length ? '#67C23A' : undefined, fontWeight: 600 }">{{ row.reviewPassed }}</span>
          </template>
        </el-table-column>
        <el-table-column label="质检" width="55" align="center" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.qualityPassed === row.details.length ? '#67C23A' : undefined, fontWeight: 600 }">{{ row.qualityPassed }}</span>
          </template>
        </el-table-column>
        <el-table-column label="验收" width="55" align="center" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.acceptancePassed === row.details.length ? '#67C23A' : undefined, fontWeight: 600 }">{{ row.acceptancePassed }}</span>
          </template>
        </el-table-column>
        <el-table-column label="全通过" width="70" align="center" sortable>
          <template #default="{ row }">
            <span :style="{ color: row.allPassedCount === row.details.length ? '#67C23A' : '#E6A23C', fontWeight: 600 }">{{ row.allPassedCount }}</span>
          </template>
        </el-table-column>
        <el-table-column label="导出" width="130">
          <template #default="{ row }">
            <div v-if="row.allPassedCount === 0" style="color:#909399;font-size:12px;">-</div>
            <div v-else-if="row.exportedCount >= row.allPassedCount" style="color:#67C23A;font-weight:600;">全部导出</div>
            <div v-else-if="row.exportedCount > 0" style="color:#E6A23C;font-weight:600;">{{ row.exportedCount }}/{{ row.allPassedCount }}</div>
            <div v-else style="color:#E6A23C;font-weight:600;">待导出</div>
          </template>
        </el-table-column>
        <el-table-column label="回传" width="100">
          <template #default="{ row }">
            <div v-if="row.exportedCount === 0" style="color:#909399;font-size:12px;">-</div>
            <div v-else-if="row.returnedCount >= row.exportedCount" style="color:#67C23A;font-weight:600;">已回传</div>
            <div v-else-if="row.returnedCount > 0" style="color:#E6A23C;font-weight:600;">{{ row.returnedCount }}/{{ row.exportedCount }}</div>
            <div v-else style="color:#909399;">未回传</div>
          </template>
        </el-table-column>
      </el-table>
    </div>
    <SnapshotDialog ref="snapshotDlg" :project-id="projectId" />
    <ExportDialog ref="exportDlg" :platform-id="platformId" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fetchItems, fetchStats, updateItemStatus, updateItemDate, batchUpdateStatus, updateTask, getExportCsvUrl, importExportCsv, startExport, getExportStatus } from '../api/index.js'
import StatsCards from './StatsCards.vue'
import EditableStatus from './EditableStatus.vue'
import EditableDate from './EditableDate.vue'
import SnapshotDialog from './SnapshotDialog.vue'
import ExportDialog from './ExportDialog.vue'

const props = defineProps({ projectId: Number, platformId: Number, user: Object })

const isInspector = computed(() => props.user?.role === 'inspector')
const exportDlg = ref(null)
const search = ref('')
const filterProcess = ref('')
const filterStatus = ref('')
const tasks = ref([])
const stats = ref({ taskCount: 0, totalItems: 0, allPassed: 0, pendingExport: 0, exported: 0, returned: 0, labelStats: {}, reviewStats: {}, qualityStats: {}, acceptanceStats: {} })
const loading = ref(false)
const statusOptions = ['未开始', '待处理', '进行中', '已通过', '已驳回']
const exportOptions = ['未导出', '已导出']
const returnOptions = ['未回传', '已回传']
const snapshotDlg = ref(null)

const batchField = ref('')
const batchValue = ref('')
const batchProcessOptions = ['未开始', '待处理', '进行中', '已通过', '已驳回']
const batchExportOptions = ['未导出', '已导出']
const batchReturnOptions = ['未回传', '已回传']
const batchOptions = ref(batchProcessOptions)

function onBatchFieldChange() {
  batchValue.value = ''
  if (batchField.value === 'exportStatus') batchOptions.value = batchExportOptions
  else if (batchField.value === 'returnStatus') batchOptions.value = batchReturnOptions
  else batchOptions.value = batchProcessOptions
}

async function doBatch(row) {
  const ids = row._selectedItems.map(d => d.id)
  if (!ids.length) return
  const value =
    batchField.value === 'exportStatus'
      ? (batchValue.value === '已导出' ? '已导出' : '')
      : batchField.value === 'returnStatus'
        ? (batchValue.value === '已回传' ? '已回传' : '')
        : batchValue.value
  try {
    await batchUpdateStatus(ids, batchField.value, value)
    ElMessage.success(`已更新 ${ids.length} 条`)
    row._selectedItems = []
    batchField.value = ''
    batchValue.value = ''
    loadAll()
  } catch (e) {
    ElMessage.error('批量更新失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadAll() {
  loading.value = true
  try {
    const [t, s] = await Promise.all([
      fetchItems(props.projectId, search.value, filterProcess.value, filterStatus.value),
      fetchStats(props.projectId),
    ])
    const data = t.data || []
    data.forEach(g => { g._selectedItems = [] })
    tasks.value = data
    stats.value = s.data
  } catch (e) {
    ElMessage.error('加载数据失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function changeStatus(d, { field, value: displayValue }) {
  const val =
    field === 'exportStatus'
      ? (displayValue === '已导出' ? '已导出' : '')
      : field === 'returnStatus'
        ? (displayValue === '已回传' ? '已回传' : '')
        : displayValue
  const date = (field === 'exportStatus' || field === 'returnStatus') && val
    ? (d[field === 'exportStatus' ? 'exportDate' : 'returnDate'] || '')
    : undefined
  updateItemStatus(d.id, field, val, date || undefined).then(loadAll).catch(() => {
    ElMessage.error('更新失败')
  })
}

function changeDate(d, field, value) {
  updateItemDate(d.id, field, value).then(loadAll).catch(() => {
    ElMessage.error('更新日期失败')
  })
}

function editTaskKey(row) {
  ElMessageBox.prompt('请输入任务 Key', '修改任务 Key', {
    inputValue: row.taskKey || '',
    confirmButtonText: '确定',
    cancelButtonText: '取消',
  }).then(async ({ value }) => {
    if (value === undefined) return
    try {
      await updateTask(row.taskId, { taskKey: value.trim() })
      ElMessage.success('Key 已更新')
      loadAll()
    } catch (e) {
      ElMessage.error('更新失败')
    }
  }).catch(() => {})
}

function downloadCsv() {
  window.open(getExportCsvUrl(props.projectId), '_blank')
}

async function handleExportCsvUpload(file) {
  const fd = new FormData()
  fd.append('file', file)
  try {
    const res = await importExportCsv(fd)
    ElMessage.success(res.data.message)
    loadAll()
  } catch (e) {
    ElMessage.error('导入失败: ' + (e.response?.data?.detail || e.message))
  }
  return false
}

function exportSelected(row) {
  const items = row._selectedItems.map(d => ({
    ...d,
    id: d.id,
    taskName: row.taskName,
    questionId: d.questionId,
    clipName: d.clipName,
  }))
  exportDlg.value?.open(items)
}

function filterPendingExport() {
  filterProcess.value = 'acceptanceStatus'
  filterStatus.value = '已通过'
  ElMessage.info('已筛选验收已通过的记录')
}

watch([search, filterProcess, filterStatus], () => { loadAll() })

const reload = () => { loadAll() }
window.__kanbanReload = reload
onMounted(() => { loadAll() })
onUnmounted(() => { delete window.__kanbanReload })
</script>

<style scoped>
.filter-bar {
  background: #fff; border-radius: 8px; padding: 10px 14px; margin-bottom: 14px;
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.table-wrap {
  background: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.batch-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  background: #ecf5ff; border: 1px solid #d9ecff; border-radius: 6px;
  padding: 8px 12px; margin-bottom: 8px;
}
.task-key { cursor: pointer; color: #409EFF; font-size: 12px; word-break: break-all; }
.task-key:hover { color: #66b1ff; text-decoration: underline; }
.task-key-empty { cursor: pointer; color: #c0c4cc; font-size: 12px; }
.task-key-empty:hover { color: #409EFF; }

</style>
