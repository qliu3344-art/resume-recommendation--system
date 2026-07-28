<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useJobDetail } from '@/composables/useJobDetail'
import JobForm from '@/components/job/JobForm.vue'
import type { JobCreate } from '@/types/job'

const router = useRouter()
const { saveLoading, create } = useJobDetail()
const formRef = ref<InstanceType<typeof JobForm> | null>(null)

async function handleSubmit() {
  const f = formRef.value!.form
  const data: JobCreate = {
    title: f.title,
    description: f.description || null,
    requirements: f.requirements?.min_education || f.requirements?.min_years || f.requirements?.required_skills?.length
      ? { ...f.requirements }
      : null,
  }
  const result = await create(data)
  ElMessage.success('岗位创建成功')
  router.push({ name: 'JobDetail', params: { id: result.id } })
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <el-button text @click="router.push({ name: 'JobList' })">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <h1 class="text-xl font-semibold">新增岗位</h1>
    </div>

    <el-card shadow="never">
      <JobForm ref="formRef" />
      <div class="mt-6 flex gap-3">
        <el-button type="primary" :loading="saveLoading" @click="handleSubmit">
          创建岗位
        </el-button>
        <el-button @click="router.push({ name: 'JobList' })">取消</el-button>
      </div>
    </el-card>
  </div>
</template>
