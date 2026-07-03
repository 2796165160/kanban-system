<template>
  <el-dialog v-model="visible" title="导出原文件（含标注结果）" width="600px" :close-on-click-modal="false" @close="handleClose">
    <div v-if="!started">
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#606266;display:block;margin-bottom:4px;">td.exe 路径</label>
        <el-input v-model="tdPath" placeholder="E:\td\td.exe" size="small" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="font-size:13px;color:#606266;display:block;margin-bottom:4px;">导出目录</label>
        <el-input v-model="outputDir" placeholder="E:\导出数据" size="small" />
      </div>
      <div style="color:#909399;font-size:12px;margin-bottom:12px;">
        共选中 <b>{{ total }}</b> 个包，同任务的包将下载到同一文件夹内
      </div>
      <div style="text-align:right;">
        <el-button size="small" @click="visible=false">取消</el-button>
        <el-button size="small" type="primary" :loading="starting" @click="handleStart">开始导出</el-button>
      </div>
    </div>

    <div v-else>
      <div style="margin-bottom:12px;">
        <el-progress :percentage="percent" :status="progressStatus" />
        <div style="font-size:13px;color:#606266;margin-top:6px;">
          已完成 {{ done }} / {{ total }}，失败 {{ failed }}
        </div>
      </div>
      <div style="max-height:300px;overflow-y:auto;border:1px solid #ebeef5;border-radius:4px;padding:8px;">
        <div v-for="item in logItems" :key="item.clipName" style="font-size:12px;padding:3px 0;display:flex;align-items:center;gap:6px;">
          <el-tag v-if="item.status==='running'" type="warning" size="small" effect="dark" style="border:0;">下载中</el-tag>
          <el-tag v-else-if="item.status==='completed'" type="success" size="small" effect="dark" style="border:0;">完成</el-tag>
          <el-tag v-else-if="item.status==='failed'" type="danger" size="small" effect="dark" style="border:0;">失败</el-tag>
          <el-tag v-else type="info" size="small" effect="dark" style="border:0;">等待</el-tag>
          <span>{{ item.taskName }} — 题{{ item.questionId }}</span>
          <span v-if="item.error" style="color:#F56C6C;margin-left:auto;">{{ item.error }}</span>
        </div>
      </div>
      <div style="text-align:right;margin-top:12px;">
        <el-button size="small" v-if="isDone" type="success" @click="openOutputDir">
          打开导出目录
        </el-button>
        <el-button size="small" @click="handleClose">关闭</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { startExport, getExportStatus } from '../api/index.js'

const props = defineProps({ platformId: Number })
const visible = ref(false)
const tdPath = ref(localStorage.getItem('tdPath') || '')
const outputDir = ref(localStorage.getItem('outputDir') || '')
const started = ref(false)
const starting = ref(false)
const exportId = ref('')
const total = ref(0)
const done = ref(0)
const failed = ref(0)
const logItems = ref([])
const isDone = ref(false)
let pollTimer = null

const percent = computed(() => {
  if (total.value === 0) return 0
  return Math.round((done.value + failed.value) / total.value * 100)
})
const progressStatus = computed(() => {
  if (isDone.value && failed.value > 0) return 'exception'
  if (isDone.value) return 'success'
  return ''
})

function open(items) {
  total.value = items.length
  done.value = 0
  failed.value = 0
  started.value = false
  starting.value = false
  exportId.value = ''
  logItems.value = items.map(i => ({
    _itemId: i.id,
    taskName: i.taskName || '',
    questionId: i.questionId || '',
    clipName: i.clipName || '',
    status: 'pending',
    error: '',
  }))
  isDone.value = false
  visible.value = true
}

async function handleStart() {
  if (!tdPath.value.trim()) { ElMessage.warning('请填写 td.exe 路径'); return }
  if (!outputDir.value.trim()) { ElMessage.warning('请填写导出目录'); return }
  localStorage.setItem('tdPath', tdPath.value)
  localStorage.setItem('outputDir', outputDir.value)

  starting.value = true
  try {
    const res = await startExport({
      tdPath: tdPath.value.trim(),
      outputDir: outputDir.value.trim(),
      platformId: props.platformId,
      itemIds: logItems.value.map(i => i._itemId || 0),
    })
    exportId.value = res.data.exportId
    started.value = true
    startPolling()
  } catch (e) {
    ElMessage.error('启动导出失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    starting.value = false
  }
}

function startPolling() {
  pollTimer = setInterval(async () => {
    try {
      const res = await getExportStatus(exportId.value)
      const data = res.data
      done.value = data.done
      failed.value = data.failed
      data.items.forEach((si, idx) => {
        if (idx < logItems.value.length) {
          logItems.value[idx].status = si.status
          logItems.value[idx].error = si.error || ''
        }
      })
      if (data.status !== 'running') {
        isDone.value = true
        clearInterval(pollTimer)
        pollTimer = null
        if (data.failed > 0) {
          ElMessage.warning(`导出完成，${data.failed} 个包失败`)
        } else {
          ElMessage.success('全部导出完成')
        }
      }
    } catch {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }, 2000)
}

function openOutputDir() {
  ElMessage.success('文件已保存至: ' + outputDir.value)
}

function handleClose() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
  visible.value = false
}

defineExpose({ open })
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>
