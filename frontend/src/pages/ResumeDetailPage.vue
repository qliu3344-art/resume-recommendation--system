<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useResumeDetail } from '@/composables/useResumeDetail'
import { resumeApi } from '@/api/resume'
import ResumeFieldsCard from '@/components/resume/ResumeFieldsCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import type { ResumeFieldsOut } from '@/types/resume'

const props = defineProps<{ id: number }>()
const { resume, loading, parseLoading, error, fetch, parse } = useResumeDetail()
const router = useRouter()

const desensitizedFields = ref<ResumeFieldsOut | null>(null)
const desensitizedLoading = ref(false)
const activeTab = ref('fields')

onMounted(() => fetch(props.id))

async function handleParse() {
  try {
    const result = await parse(props.id)
    ElMessage.success(result.message || '解析完成')
  } catch {
    // 错误由拦截器处理
  }
}

async function handleViewDesensitized() {
  desensitizedLoading.value = true
  try {
    desensitizedFields.value = await resumeApi.getDesensitized(props.id)
  } finally {
    desensitizedLoading.value = false
  }
}
</script>

<template>
  <div>
    <!-- 头部 -->
    <div class="flex items-center gap-3 mb-4">
      <el-button text @click="router.push({ name: 'ResumeList' })">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <h1 class="text-xl font-semibold">简历详情</h1>
    </div>

    <!-- Error -->
    <el-result
      v-if="error"
      icon="error"
      title="加载失败"
      :sub-title="error"
    >
      <template #extra>
        <el-button type="primary" @click="fetch(props.id)">重新加载</el-button>
        <el-button @click="router.push({ name: 'ResumeList' })">返回列表</el-button>
      </template>
    </el-result>

    <!-- Loading -->
    <LoadingSkeleton v-else-if="loading" :rows="8" />

    <!-- Content -->
    <template v-else-if="resume">
      <el-card shadow="never" class="mb-4">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-3">
              <span class="font-semibold">{{ resume.filename }}</span>
              <StatusTag :status="resume.status" />
            </div>
            <div class="flex gap-2">
              <el-button
                v-if="resume.status !== 'verified'"
                type="primary"
                :loading="parseLoading"
                @click="handleParse"
              >
                {{ resume.status === 'uploaded' ? 'AI 解析' : '重新解析' }}
              </el-button>
              <el-button
                v-if="resume.fields"
                :loading="desensitizedLoading"
                @click="handleViewDesensitized"
              >
                查看脱敏数据
              </el-button>
            </div>
          </div>
        </template>

        <el-tabs v-model="activeTab">
          <el-tab-pane label="结构化字段" name="fields">
            <ResumeFieldsCard v-if="resume.fields" :fields="resume.fields" />
            <el-empty v-else description="尚未解析，请点击 AI 解析按钮" :image-size="80" />
          </el-tab-pane>

          <el-tab-pane label="简历原文" name="raw">
            <div class="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
              <pre class="text-sm text-gray-700 whitespace-pre-wrap font-sans">{{ resume.raw_text || '暂无原文' }}</pre>
            </div>
          </el-tab-pane>

          <el-tab-pane v-if="desensitizedFields" label="脱敏数据" name="desensitized">
            <el-alert type="info" :closable="false" class="mb-4">
              以下为脱敏后的数据，敏感信息已遮盖
            </el-alert>
            <ResumeFieldsCard :fields="desensitizedFields" />
          </el-tab-pane>
        </el-tabs>
      </el-card>
    </template>
  </div>
</template>
