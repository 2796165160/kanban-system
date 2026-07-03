<template>
  <el-dropdown v-if="!disabled" trigger="click" @command="select">
    <el-tag
      :type="tagType"
      size="small"
      class="editable-tag"
      @click.prevent
    >
      {{ currentDisplay }}
    </el-tag>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="opt in options"
          :key="opt"
          :command="opt"
          :disabled="opt === currentDisplay"
        >
          <el-tag :type="tagTypeFor(opt)" size="small" style="cursor:pointer;">{{ opt }}</el-tag>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
  <el-tag v-else :type="tagType" size="small" style="cursor:default;">
    {{ currentDisplay }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: String,
  options: { type: Array, default: () => ['未开始', '待处理', '进行中', '已通过', '已驳回'] },
  field: { type: String, required: true },
  disabled: { type: Boolean, default: false },
})
const emit = defineEmits(['change'])

const currentDisplay = computed(() => props.status || props.options[0])

function tagTypeFor(s) {
  if (!s) return 'info'
  if (s === '未开始' || s === '未导出' || s === '未回传') return 'info'
  if (s === '待处理') return 'warning'
  if (s === '进行中') return 'primary'
  if (s === '已通过' || s === '已导出' || s === '已回传') return 'success'
  if (s === '已驳回') return 'danger'
  return 'info'
}

const tagType = computed(() => tagTypeFor(currentDisplay.value))

function select(opt) {
  if (opt === currentDisplay.value) return
  emit('change', { field: props.field, value: opt })
}
</script>

<style scoped>
.editable-tag { cursor: pointer; transition: box-shadow 0.2s; }
.editable-tag:hover { box-shadow: 0 0 0 2px rgba(64,158,255,0.4); }
</style>
