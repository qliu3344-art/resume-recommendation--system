<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMatch } from '@/composables/useMatch'
import MatchResultTable from '@/components/match/MatchResultTable.vue'
import LoadingSkeleton from '@/components/common/LoadingSkeleton.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const props = defineProps<{ jobId: number }>()
const router = useRouter()
const { results, jobTitle, totalMatches, loading, fetchResults } = useMatch()

onMounted(() => fetchResults(props.jobId))
</script>

<template>
  <div>
    <div class="flex items-center gap-3 mb-4">
      <el-button text @click="router.push({ name: 'JobDetail', params: { id: jobId } })">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <h1 class="text-xl font-semibold">匹配结果 — {{ jobTitle || '加载中...' }}</h1>
    </div>

    <el-card shadow="never">
      <LoadingSkeleton v-if="loading" :rows="5" />
      <EmptyState
        v-else-if="results.length === 0"
        description="暂无匹配结果"
        action-label="返回岗位详情"
        @action="router.push({ name: 'JobDetail', params: { id: jobId } })"
      />
      <template v-else>
        <div class="mb-3 text-sm text-gray-500">
          共匹配 <strong class="text-primary">{{ totalMatches }}</strong> 名候选人
        </div>
        <MatchResultTable :results="results" :loading="false" />
      </template>
    </el-card>
  </div>
</template>
