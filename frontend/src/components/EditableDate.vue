<template>
  <el-date-picker
    v-model="localDate"
    type="date"
    size="small"
    placeholder="选择日期"
    value-format="YYYY-MM-DD"
    style="width:115px;"
    @change="onChange"
  />
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({ date: String })
const emit = defineEmits(['change'])

const localDate = ref(props.date || '')

watch(() => props.date, (v) => { localDate.value = v || '' })

function onChange(val) {
  emit('change', val || '')
}
</script>
