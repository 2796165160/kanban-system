<template>
  <el-dialog v-model="visible" title="快照历史" width="650px" :close-on-click-modal="false">
    <div v-if="loading" style="text-align:center;padding:30px;color:#909399;">加载中...</div>
    <div v-else-if="snapshots.length === 0" style="text-align:center;padding:30px;color:#c0c4cc;">
      暂无快照，请先执行数据拉取
    </div>
    <div v-else>
      <el-table :data="snapshots" size="small" border style="width:100%;" @row-click="viewSnapshot">
        <el-table-column prop="snapshotAt" label="快照时间" min-width="160" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" text type="primary" @click="viewSnapshot(row)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="detailVisible" title="快照详情" width="550px" append-to-body>
      <el-table v-if="snapshotTasks.length" :data="snapshotTasks" size="small" border style="width:100%;">
        <el-table-column prop="taskName" label="任务名称" min-width="120" />
        <el-table-column prop="total" label="总题" width="50" align="center" />
        <el-table-column label="标注" width="50" align="center">
          <template #default="{ row }">{{ row.labelPassed }}</template>
        </el-table-column>
        <el-table-column label="审核" width="50" align="center">
          <template #default="{ row }">{{ row.reviewPassed }}</template>
        </el-table-column>
        <el-table-column label="质检" width="50" align="center">
          <template #default="{ row }">{{ row.qualityPassed }}</template>
        </el-table-column>
        <el-table-column label="验收" width="50" align="center">
          <template #default="{ row }">{{ row.acceptancePassed }}</template>
        </el-table-column>
      </el-table>
      <div v-else style="text-align:center;padding:20px;color:#909399;">暂无数据</div>
    </el-dialog>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchSnapshots, fetchSnapshotTasks } from '../api/index.js'

const props = defineProps({ projectId: Number })
const visible = ref(false)
const loading = ref(false)
const snapshots = ref([])
const detailVisible = ref(false)
const snapshotTasks = ref([])

async function load() {
  loading.value = true
  try {
    const res = await fetchSnapshots(props.projectId)
    snapshots.value = res.data || []
  } catch { /* ignore */ }
  finally { loading.value = false }
}

async function viewSnapshot(s) {
  try {
    const res = await fetchSnapshotTasks(s.id)
    snapshotTasks.value = res.data || []
    detailVisible.value = true
  } catch { ElMessage.error('加载快照详情失败') }
}

function open() {
  visible.value = true
  load()
}

defineExpose({ open })
</script>
