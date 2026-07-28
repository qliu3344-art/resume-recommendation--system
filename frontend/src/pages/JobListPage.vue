<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useJobs } from '@/composables/useJobs'
import { jobApi } from '@/api/job'
import JobTable from '@/components/job/JobTable.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const { items, total, loading, page, pageSize, fetch, onPageChange } = useJobs()
const router = useRouter()

onMounted(() => fetch())

async function handleDelete(id: number) {
  await jobApi.delete(id)
  ElMessage.success('岗位已删除')
  fetch()
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-semibold">岗位管理</h1>
      <el-button type="primary" @click="router.push({ name: 'JobCreate' })">
        <el-icon class="mr-1"><Plus /></el-icon>
        新增岗位
      </el-button>
    </div>

    <el-card shadow="never">
      <template v-if="total === 0 && !loading">
        <EmptyState
          description="暂无岗位数据，请创建岗位开始匹配"
          action-label="新增岗位"
          @action="router.push({ name: 'JobCreate' })"
        />
      </template>
      <template v-else>
        <JobTable :items="items" :loading="loading" @delete="handleDelete" />
        <div class="flex justify-end mt-4">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            layout="total, prev, pager, next"
            @current-change="onPageChange"
          />
        </div>
      </template>
    </el-card>
  </div>
</template>
