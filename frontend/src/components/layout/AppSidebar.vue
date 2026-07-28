<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const menuItems = [
  { path: '/resumes', title: '简历管理', icon: 'Document' },
  { path: '/jobs', title: '岗位管理', icon: 'Briefcase' },
]

function isActive(path: string) {
  return route.path.startsWith(path)
}
</script>

<template>
  <div class="flex flex-col h-full">
    <div class="h-14 flex items-center px-5 border-b border-gray-100">
      <span class="text-lg font-semibold text-primary">📄 简历推荐系统</span>
    </div>
    <el-menu
      :default-active="route.path"
      router
      class="flex-1 border-r-0"
      background-color="transparent"
    >
      <el-menu-item
        v-for="item in menuItems"
        :key="item.path"
        :index="item.path"
        class="mx-2 rounded-lg mb-1"
      >
        <el-icon class="mr-2"><component :is="item.icon" /></el-icon>
        <span>{{ item.title }}</span>
      </el-menu-item>
    </el-menu>
    <div class="p-4 border-t border-gray-100">
      <p class="text-xs text-gray-400">智能简历推荐系统 v1.0</p>
    </div>
  </div>
</template>
