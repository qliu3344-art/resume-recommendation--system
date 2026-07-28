<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useResumes } from '@/composables/useResumes'
import { useUpload } from '@/composables/useUpload'
import ResumeTable from '@/components/resume/ResumeTable.vue'
import ResumeUploadDialog from '@/components/resume/ResumeUploadDialog.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const { items, total, loading, page, pageSize, fetch, onPageChange, onPageSizeChange } = useResumes()
const { uploading, upload } = useUpload()
const uploadVisible = ref(false)

onMounted(() => fetch())

async function handleUpload(file: File) {
  await upload(file)
  uploadVisible.value = false
  ElMessage.success('简历上传成功')
  page.value = 1
  fetch()
}
</script>

<template>
  <div>
    <div class="flex items-center justify-between mb-4">
      <h1 class="text-xl font-semibold">简历管理</h1>
      <el-button type="primary" @click="uploadVisible = true">
        <el-icon class="mr-1"><Upload /></el-icon>
        上传简历
      </el-button>
    </div>

    <el-card shadow="never">
      <template v-if="total === 0 && !loading">
        <EmptyState
          description="暂无简历数据，请上传简历开始使用"
          action-label="上传简历"
          @action="uploadVisible = true"
        />
      </template>
      <template v-else>
        <ResumeTable :items="items" :loading="loading" />
        <div class="flex justify-end mt-4">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50]"
            layout="total, sizes, prev, pager, next"
            @current-change="onPageChange"
            @size-change="onPageSizeChange"
          />
        </div>
      </template>
    </el-card>

    <ResumeUploadDialog
      v-model:visible="uploadVisible"
      :uploading="uploading"
      @upload="handleUpload"
    />
  </div>
</template>
