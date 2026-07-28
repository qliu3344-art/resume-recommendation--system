<script setup lang="ts">
import type { ResumeUploadResponse } from '@/types/resume'
import StatusTag from '@/components/common/StatusTag.vue'
import { useRouter } from 'vue-router'

defineProps<{
  items: ResumeUploadResponse[]
  loading: boolean
}>()

const router = useRouter()

function toDetail(id: number) {
  router.push({ name: 'ResumeDetail', params: { id } })
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}
</script>

<template>
  <el-table
    :data="items"
    v-loading="loading"
    stripe
    highlight-current-row
    class="w-full"
    @row-click="(row: ResumeUploadResponse) => toDetail(row.id)"
    row-class-name="cursor-pointer"
  >
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="filename" label="文件名" min-width="200" show-overflow-tooltip />
    <el-table-column prop="status" label="状态" width="100">
      <template #default="{ row }">
        <StatusTag :status="row.status" />
      </template>
    </el-table-column>
    <el-table-column prop="created_at" label="上传时间" width="180">
      <template #default="{ row }">
        {{ formatDate(row.created_at) }}
      </template>
    </el-table-column>
    <el-table-column label="操作" width="100" fixed="right">
      <template #default="{ row }">
        <el-button text type="primary" size="small" @click.stop="toDetail(row.id)">
          查看
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
