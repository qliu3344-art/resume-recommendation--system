<script setup lang="ts">
defineProps<{
  score: number
}>()

function scoreLabel(s: number) {
  if (s >= 0.8) return '优秀'
  if (s >= 0.6) return '良好'
  if (s >= 0.4) return '一般'
  return '较低'
}

function scoreType(s: number): '' | 'success' | 'warning' | 'danger' {
  if (s >= 0.8) return 'success'
  if (s >= 0.6) return ''
  if (s >= 0.4) return 'warning'
  return 'danger'
}
</script>

<template>
  <span class="inline-flex items-center gap-1.5">
    <el-tag :type="scoreType(score)" size="small" effect="dark">
      {{ (score * 100).toFixed(0) }}%
    </el-tag>
    <span class="text-xs" :class="{
      'text-green-600': score >= 0.8,
      'text-blue-600': score >= 0.6 && score < 0.8,
      'text-orange-500': score >= 0.4 && score < 0.6,
      'text-red-500': score < 0.4,
    }">{{ scoreLabel(score) }}</span>
  </span>
</template>
