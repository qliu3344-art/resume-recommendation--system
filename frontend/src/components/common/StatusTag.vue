<script setup lang="ts">
import type { ResumeStatus } from '@/types/resume'

defineProps<{
  status: ResumeStatus
}>()

const statusMap: Record<ResumeStatus, { text: string; type: 'info' | 'warning' | 'success' }> = {
  uploaded: { text: '待解析', type: 'info' },
  parsed: { text: '已解析', type: 'warning' },
  verified: { text: '已校验', type: 'success' },
}
</script>

<template>
  <el-tag :type="statusMap[status].type" size="small" effect="plain">
    {{ statusMap[status].text }}
  </el-tag>
</template>
