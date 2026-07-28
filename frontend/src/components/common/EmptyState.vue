<script setup lang="ts">
defineProps<{
  description: string
  actionLabel?: string
}>()

defineEmits<{
  action: []
}>()
</script>

<template>
  <el-empty :description="description" :image-size="120">
    <template v-if="actionLabel">
      <el-button type="primary" @click="$emit('action')">
        {{ actionLabel }}
      </el-button>
    </template>
  </el-empty>
</template>
