<script setup lang="ts">
withDefaults(defineProps<{
  rows?: number
  animated?: boolean
}>(), {
  rows: 5,
  animated: true,
})
</script>

<template>
  <div class="space-y-3 p-4">
    <el-skeleton :rows="rows" :animated="animated" />
  </div>
</template>
