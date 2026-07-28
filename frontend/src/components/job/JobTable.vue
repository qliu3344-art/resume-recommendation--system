<script setup lang="ts">
import type { JobOut } from '@/types/job'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'

defineProps<{
  items: JobOut[]
  loading: boolean
}>()

const emit = defineEmits<{
  delete: [id: number]
}>()

const router = useRouter()

function formatDate(iso: string) {
  return new Date(iso).toLocaleString('zh-CN')
}

async function confirmDelete(id: number, title: string) {
  try {
    await ElMessageBox.confirm(`确定要删除岗位「${title}」吗？此操作不可恢复。`, '确认删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    emit('delete', id)
  } catch {
    // 取消
  }
}
</script>

<template>
  <el-table :data="items" v-loading="loading" stripe highlight-current-row class="w-full">
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="title" label="岗位名称" min-width="200" show-overflow-tooltip>
      <template #default="{ row }">
        <router-link
          :to="{ name: 'JobDetail', params: { id: row.id } }"
          class="text-primary hover:underline font-medium"
        >
          {{ row.title }}
        </router-link>
      </template>
    </el-table-column>
    <el-table-column prop="description" label="岗位描述" min-width="300" show-overflow-tooltip />
    <el-table-column prop="created_at" label="创建时间" width="180">
      <template #default="{ row }">
        {{ formatDate(row.created_at) }}
      </template>
    </el-table-column>
    <el-table-column label="操作" width="200" fixed="right">
      <template #default="{ row }">
        <el-button text type="primary" size="small" @click="router.push({ name: 'JobDetail', params: { id: row.id } })">
          详情
        </el-button>
        <el-button text size="small" @click="router.push({ name: 'JobEdit', params: { id: row.id } })">
          编辑
        </el-button>
        <el-button text type="danger" size="small" @click="confirmDelete(row.id, row.title)">
          删除
        </el-button>
      </template>
    </el-table-column>
  </el-table>
</template>
