<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useJobDetail } from '@/composables/useJobDetail'
import { useMatch } from '@/composables/useMatch'
import MatchResultTable from '@/components/match/MatchResultTable.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'

const props = defineProps<{ id: number }>()
const router = useRouter()
const { job, loading, error, fetch, remove } = useJobDetail()
const { results, loading: matchLoading, runLoading, fetchResults, run } = useMatch()

onMounted(async () => {
  await fetch(props.id)
  fetchResults(props.id)
})

async function handleDelete() {
  try {
    await ElMessageBox.confirm(
      `确定要删除岗位「${job.value?.title}」吗？相关匹配记录也将被删除。`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await remove(props.id)
    ElMessage.success('岗位已删除')
    router.push({ name: 'JobList' })
  } catch { /* 取消 */ }
}

async function handleMatch() {
  const res = await run(props.id)
  ElMessage.success(`匹配完成，共 ${res.total_matches} 名候选人`)
}
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <el-button text @click="router.push({ name: 'JobList' })">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <h1 class="text-xl font-semibold">岗位详情</h1>
    </div>

    <el-result v-if="error" icon="error" title="加载失败" :sub-title="error" />
    <LoadingSkeleton v-else-if="loading" :rows="6" />

    <template v-else-if="job">
      <!-- 岗位信息 -->
      <el-card shadow="never" class="mb-4">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-semibold text-lg">{{ job.title }}</span>
            <div class="flex gap-2">
              <el-button @click="router.push({ name: 'JobEdit', params: { id } })">编辑</el-button>
              <el-button type="danger" @click="handleDelete">删除</el-button>
            </div>
          </div>
        </template>

        <el-descriptions :column="2" border>
          <el-descriptions-item label="岗位描述" :span="2">
            {{ job.description || '暂无描述' }}
          </el-descriptions-item>
          <el-descriptions-item label="最低学历">
            {{ job.requirements?.min_education || '不限' }}
          </el-descriptions-item>
          <el-descriptions-item label="最低工作年限">
            {{ job.requirements?.min_years ? job.requirements.min_years + ' 年' : '不限' }}
          </el-descriptions-item>
          <el-descriptions-item label="必备技能" :span="2">
            <template v-if="job.requirements?.required_skills?.length">
              <el-tag
                v-for="skill in job.requirements.required_skills"
                :key="skill"
                size="small"
                class="mr-1 mb-1"
              >
                {{ skill }}
              </el-tag>
            </template>
            <span v-else class="text-gray-400">不限</span>
          </el-descriptions-item>
          <el-descriptions-item label="创建时间">
            {{ new Date(job.created_at).toLocaleString('zh-CN') }}
          </el-descriptions-item>
        </el-descriptions>
      </el-card>

      <!-- 匹配区域 -->
      <el-card shadow="never">
        <template #header>
          <div class="flex items-center justify-between">
            <span class="font-semibold">候选人匹配</span>
            <el-button type="primary" :loading="runLoading" @click="handleMatch">
              <el-icon class="mr-1"><Search /></el-icon>
              开始匹配
            </el-button>
          </div>
        </template>

        <template v-if="results.length > 0">
          <MatchResultTable :results="results" :loading="matchLoading || runLoading" />
        </template>
        <template v-else>
          <el-empty description="尚未进行匹配，请点击「开始匹配」按钮" :image-size="80" />
        </template>

        <div v-if="results.length > 0" class="mt-3 text-right">
          <el-button text type="primary" @click="router.push({ name: 'MatchResults', params: { id } })">
            查看完整匹配结果
            <el-icon class="ml-1"><ArrowRight /></el-icon>
          </el-button>
        </div>
      </el-card>
    </template>
  </div>
</template>
