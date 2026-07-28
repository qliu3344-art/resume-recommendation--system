<script setup lang="ts">
import type { MatchResult } from '@/types/job'
import ScoreBadge from '@/components/common/ScoreBadge.vue'

defineProps<{
  results: MatchResult[]
  loading: boolean
}>()
</script>

<template>
  <el-table :data="results" v-loading="loading" stripe class="w-full" default-sort="{ prop: 'total_score', order: 'descending' }">
    <el-table-column label="排名" width="60">
      <template #default="{ $index }">{{ $index + 1 }}</template>
    </el-table-column>
    <el-table-column prop="name" label="候选人" width="120">
      <template #default="{ row }">
        <span class="font-medium">{{ row.name || '未知' }}</span>
      </template>
    </el-table-column>
    <el-table-column prop="keyword_score" label="关键词匹配" width="140" sortable>
      <template #default="{ row }">
        <ScoreBadge :score="row.keyword_score" />
      </template>
    </el-table-column>
    <el-table-column prop="semantic_score" label="语义匹配" width="140" sortable>
      <template #default="{ row }">
        <ScoreBadge :score="row.semantic_score" />
      </template>
    </el-table-column>
    <el-table-column prop="total_score" label="综合评分" width="140" sortable>
      <template #default="{ row }">
        <el-progress
          :percentage="Math.round(row.total_score * 100)"
          :status="row.total_score >= 0.8 ? 'success' : row.total_score >= 0.6 ? '' : 'warning'"
          :stroke-width="8"
        />
      </template>
    </el-table-column>
    <el-table-column label="匹配详情" min-width="200">
      <template #default="{ row }">
        <div v-if="row.match_details" class="text-xs text-gray-600">
          <template v-if="row.match_details.reason">{{ row.match_details.reason }}</template>
          <template v-else>
            <span v-if="row.match_details.education" class="block">{{ row.match_details.education }}</span>
            <span v-if="row.match_details.years" class="block">{{ row.match_details.years }}</span>
            <span v-if="row.match_details.skills" class="block">{{ row.match_details.skills }}</span>
          </template>
        </div>
        <span v-else class="text-gray-400">-</span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="100" fixed="right">
      <template #default="{ row }">
        <router-link
          :to="{ name: 'ResumeDetail', params: { id: row.resume_id } }"
          class="text-primary text-sm hover:underline"
        >
          查看简历
        </router-link>
      </template>
    </el-table-column>
  </el-table>
</template>
