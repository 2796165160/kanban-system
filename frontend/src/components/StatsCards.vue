<template>
  <div class="stats-wrap">
    <el-row :gutter="8">
      <el-col :xs="12" :sm="8" :md="4" v-for="card in metricCards" :key="card.label">
        <div class="metric-card">
          <div class="metric-value" :style="{ color: card.color }">{{ card.value }}</div>
          <div class="metric-label">{{ card.label }}</div>
        </div>
      </el-col>
    </el-row>

    <div class="process-panel">
      <div class="panel-header">工序状态明细</div>
      <div class="process-row" v-for="proc in processes" :key="proc.key">
        <div class="proc-name">{{ proc.label }}</div>
        <div class="proc-statuses">
          <span v-for="s in (isInspector ? inspectorStatusLabels : statusLabels)" :key="s" class="status-tag" :class="'tag-' + s">
            <span class="tag-count">{{ (stats[proc.key] || {})[s] ?? 0 }}</span>
            <span class="tag-label">{{ s }}</span>
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ stats: Object, user: Object })

const statusLabels = ['未开始', '待处理', '进行中', '已通过', '已驳回']
const inspectorStatusLabels = ['进行中', '已通过', '已驳回']

const isInspector = computed(() => props.user?.role === 'inspector')

const processes = computed(() => {
  if (isInspector.value) {
    return [
      { label: '质检', key: 'qualityStats' },
      { label: '验收', key: 'acceptanceStats' },
    ]
  }
  return [
    { label: '标注', key: 'labelStats' },
    { label: '审核', key: 'reviewStats' },
    { label: '质检', key: 'qualityStats' },
    { label: '验收', key: 'acceptanceStats' },
  ]
})

const metricCards = computed(() => [
  { label: '任务数', value: props.stats.taskCount ?? 0, color: '#409EFF' },
  { label: '总数据量', value: props.stats.totalItems ?? 0, color: '#409EFF' },
  { label: '全通过', value: props.stats.allPassed ?? 0, color: '#67C23A' },
  { label: '待导出', value: props.stats.pendingExport ?? 0, color: '#E6A23C' },
  { label: '已导出', value: props.stats.exported ?? 0, color: '#9b59b6' },
  { label: '已回传', value: props.stats.returned ?? 0, color: '#00a8a8' },
])
</script>

<style scoped>
.stats-wrap { display: flex; flex-direction: column; gap: 16px; }

.metric-card {
  background: #fff;
  border-radius: 10px;
  padding: 16px 8px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  transition: transform .2s, box-shadow .2s;
}
.metric-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.08);
}
.metric-value { font-size: 26px; font-weight: 700; line-height: 1.3; }
.metric-label { font-size: 12px; color: #909399; margin-top: 2px; }

.process-panel {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  overflow: hidden;
}
.panel-header {
  padding: 12px 20px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  border-bottom: 1px solid #f0f0f0;
  background: #fafafa;
}
.process-row {
  display: flex;
  align-items: center;
  padding: 10px 20px;
  gap: 16px;
  transition: background .15s;
}
.process-row + .process-row { border-top: 1px solid #f5f5f5; }
.process-row:hover { background: #f8f9fb; }
.proc-name {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  min-width: 44px;
}
.proc-statuses {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 14px;
  font-size: 12px;
  color: #fff;
  font-weight: 500;
  line-height: 1.4;
}
.tag-count { font-size: 14px; font-weight: 700; }
.tag-label { opacity: .85; }

.tag-未开始 { background: #909399; }
.tag-待处理 { background: #409EFF; }
.tag-进行中 { background: #E6A23C; }
.tag-已通过 { background: #67C23A; }
.tag-已驳回 { background: #F56C6C; }
</style>
