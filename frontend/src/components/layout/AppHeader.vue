<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()

const breadcrumbItems = computed(() => {
  const items: { title: string; path?: string }[] = []
  const matched = route.matched

  for (const record of matched) {
    items.push({
      title: (record.meta.title as string) ?? record.name?.toString() ?? '',
      path: record.path,
    })
  }
  return items
})
</script>

<template>
  <div class="flex items-center justify-between w-full">
    <el-breadcrumb separator="/">
      <el-breadcrumb-item
        v-for="(item, index) in breadcrumbItems"
        :key="index"
        :to="index < breadcrumbItems.length - 1 ? item.path : undefined"
      >
        {{ item.title }}
      </el-breadcrumb-item>
    </el-breadcrumb>
    <span class="text-sm text-gray-400">智能简历推荐系统</span>
  </div>
</template>
