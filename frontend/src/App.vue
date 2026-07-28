<script setup lang="ts">
import AppSidebar from '@/components/layout/AppSidebar.vue'
import AppHeader from '@/components/layout/AppHeader.vue'
</script>

<template>
  <el-container class="h-screen">
    <el-aside width="220px" class="bg-white border-r border-gray-200">
      <AppSidebar />
    </el-aside>
    <el-container>
      <el-header height="56px" class="bg-white border-b border-gray-200 px-6 flex items-center">
        <AppHeader />
      </el-header>
      <el-main class="bg-[#f5f7fa] p-6">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>
