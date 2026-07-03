<template>
  <el-dialog v-model="visible" :title="'平台连接配置 - ' + (platform?.name || '')" width="520px" :close-on-click-modal="false">
    <el-tabs v-model="activeTab" style="margin-top:-8px;">
      <el-tab-pane label="连接配置" name="conn">
        <el-form label-width="80px">
          <el-form-item label="平台地址">
            <el-input v-model="form.baseUrl" placeholder="http://14.103.128.193:8080" size="default" />
          </el-form-item>
          <el-form-item label="Access Key">
            <el-input v-model="form.accessKey" placeholder="从 Network 请求头复制 access-key" size="default" show-password />
          </el-form-item>
          <el-form-item label="定时拉取">
            <el-input v-model="form.scheduleTimes" placeholder="如 12:00,18:00（逗号分隔，留空则不定时）" size="default" />
          </el-form-item>
          <el-form-item>
            <div style="display:flex;gap:8px;flex-wrap:wrap;">
              <el-button type="primary" :loading="testing" @click="handleTest">测试连接</el-button>
              <el-button type="success" :loading="saving" @click="handleSave">保存配置</el-button>
              <el-button type="warning" :loading="fetching" @click="handleFetch">立即拉取数据</el-button>
            </div>
          </el-form-item>
        </el-form>
        <div v-if="testResult" :class="['test-result', testResult.ok ? 'ok' : 'fail']">
          <el-icon v-if="testResult.ok"><CircleCheck /></el-icon>
          <el-icon v-else><WarningFilled /></el-icon>
          {{ testResult.msg }}
        </div>
      </el-tab-pane>
      <el-tab-pane label="拉取结果" name="log">
        <div v-if="!fetchResult || fetchResult.length === 0" style="text-align:center;padding:20px;color:#909399;">暂无拉取记录，请先执行拉取</div>
        <div v-else class="fetch-log">
          <div v-for="r in fetchResult" :key="r.task" style="font-size:12px;padding:3px 0;border-bottom:1px solid #f0f0f0;">
            <span v-if="r.status === 'ok'" style="color:#67C23A;">✓ {{ r.task }}</span>
            <span v-else style="color:#F56C6C;">✗ {{ r.task }}: {{ r.error }}</span>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { updatePlatformConnection, getPlatformConnection, testPlatformConnection, fetchPlatformData, getPlatformSchedule, updatePlatformSchedule } from '../api/index.js'

const props = defineProps({ platform: Object })
const emit = defineEmits(['saved'])

const visible = ref(false)
const activeTab = ref('conn')
const form = ref({ baseUrl: '', accessKey: '', scheduleTimes: '' })
const testing = ref(false)
const saving = ref(false)
const fetching = ref(false)
const testResult = ref(null)
const fetchResult = ref(null)

watch(() => props.platform, (p) => {
  if (p) { loadConnection(p.id) }
})

async function loadConnection(id) {
  try {
    const [conn, sched] = await Promise.all([
      getPlatformConnection(id),
      getPlatformSchedule(id).then(r => r.data).catch(() => ({ scheduleTimes: '' }))
    ])
    form.value.baseUrl = conn.data.baseUrl || ''
    form.value.accessKey = ''
    form.value.scheduleTimes = sched.scheduleTimes || ''
  } catch { /* ignore */ }
}

async function handleTest() {
  if (!form.value.baseUrl) { ElMessage.warning('请输入平台地址'); return }
  testing.value = true; testResult.value = null
  try {
    await saveConfig()
    const res = await testPlatformConnection(props.platform.id)
    testResult.value = { ok: true, msg: res.data.message || '连接成功' }
  } catch (e) {
    testResult.value = { ok: false, msg: e.response?.data?.detail || '连接失败' }
  } finally { testing.value = false }
}

async function saveConfig() {
  await updatePlatformConnection(props.platform.id, form.value.baseUrl, form.value.accessKey)
  await updatePlatformSchedule(props.platform.id, form.value.scheduleTimes)
}

async function handleSave() {
  if (!form.value.baseUrl) { ElMessage.warning('请输入平台地址'); return }
  saving.value = true
  try {
    await saveConfig()
    ElMessage.success('配置已保存')
    emit('saved')
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally { saving.value = false }
}

async function handleFetch() {
  fetching.value = true; fetchResult.value = null
  try {
    await saveConfig()
    const res = await fetchPlatformData(props.platform.id)
    fetchResult.value = res.data.results || []
    activeTab.value = 'log'
    ElMessage.success(res.data.message || '拉取完成')
    emit('saved')
  } catch (e) {
    ElMessage.error('拉取失败: ' + (e.response?.data?.detail || e.message))
  } finally { fetching.value = false }
}

function open() {
  visible.value = true; activeTab.value = 'conn'
  testResult.value = null; fetchResult.value = null
  if (props.platform) loadConnection(props.platform.id)
}

defineExpose({ open })
</script>

<style scoped>
.test-result { margin-top: 8px; padding: 8px 12px; border-radius: 4px; font-size: 13px; display: flex; align-items: center; gap: 6px; }
.test-result.ok { background: #f0f9eb; color: #67C23A; }
.test-result.fail { background: #fef0f0; color: #F56C6C; }
.fetch-log { background: #f5f7fa; border-radius: 4px; padding: 8px; max-height: 350px; overflow-y: auto; }
</style>
