<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useJobDetail } from '@/composables/useJobDetail'
import JobForm from '@/components/job/JobForm.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'

const props = defineProps<{ id: number }>()
const router = useRouter()
const { job, loading, saveLoading, error, fetch, update } = useJobDetail()
const formRef = ref<InstanceType<typeof JobForm> | null>(null)

onMounted(async () => {
  await fetch(props.id)
  if (job.value) {
    const f = formRef.value!.form
    f.title = job.value.title
    f.description = job.value.description ?? ''
    f.requirements!.min_education = job.value.requirements?.min_education ?? ''
    f.requirements!.min_years = job.value.requirements?.min_years ?? 0
    f.requirements!.required_skills = job.value.requirements?.required_skills ?? []
  }
})

async function handleSubmit() {
  const f = formRef.value!.form
  await update(props.id, {
    title: f.title,
    description: f.description || null,
    requirements: f.requirements,
  })
  ElMessage.success('岗位更新成功')
  router.push({ name: 'JobDetail', params: { id: props.id } })
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <el-button text @click="router.push({ name: 'JobDetail', params: { id } })">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <h1 class="text-xl font-semibold">编辑岗位</h1>
    </div>

    <el-result
      v-if="error"
      icon="error"
      title="加载失败"
      :sub-title="error"
    />

    <LoadingSkeleton v-else-if="loading" :rows="6" />

    <el-card v-else shadow="never">
      <JobForm ref="formRef" />
      <div class="mt-6 flex gap-3">
        <el-button type="primary" :loading="saveLoading" @click="handleSubmit">
          保存修改
        </el-button>
        <el-button @click="router.push({ name: 'JobDetail', params: { id } })">取消</el-button>
      </div>
    </el-card>
  </div>
</template>
