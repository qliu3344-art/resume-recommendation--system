<script setup lang="ts">
import type { ResumeFieldsOut } from '@/types/resume'

defineProps<{
  fields: ResumeFieldsOut
}>()
</script>

<template>
  <el-descriptions :column="2" border size="default" title="结构化字段">
    <el-descriptions-item label="姓名">
      {{ fields.name || '-' }}
    </el-descriptions-item>
    <el-descriptions-item label="学历">
      <el-tag v-if="fields.education" size="small">{{ fields.education }}</el-tag>
      <span v-else>-</span>
    </el-descriptions-item>
    <el-descriptions-item label="手机号">
      {{ fields.phone || '-' }}
    </el-descriptions-item>
    <el-descriptions-item label="邮箱">
      {{ fields.email || '-' }}
    </el-descriptions-item>
    <el-descriptions-item label="学校">
      {{ fields.school || '-' }}
    </el-descriptions-item>
    <el-descriptions-item label="专业">
      {{ fields.major || '-' }}
    </el-descriptions-item>
    <el-descriptions-item label="毕业年份">
      {{ fields.graduation_year ?? '-' }}
    </el-descriptions-item>
    <el-descriptions-item label="是否重复">
      <el-tag v-if="fields.is_duplicate" type="warning" size="small">疑似重复</el-tag>
      <el-tag v-else type="success" size="small">唯一</el-tag>
    </el-descriptions-item>
  </el-descriptions>

  <!-- 工作经历 -->
  <div v-if="fields.work_experience?.length" class="mt-5">
    <h4 class="text-sm font-medium text-gray-700 mb-3">工作经历</h4>
    <el-timeline>
      <el-timeline-item
        v-for="(exp, idx) in fields.work_experience"
        :key="idx"
        :timestamp="exp.period"
        placement="top"
        color="#409eff"
      >
        <div class="text-sm font-medium">{{ exp.company }}</div>
        <div class="text-xs text-gray-500">{{ exp.position }}</div>
        <div v-if="exp.description" class="text-xs text-gray-400 mt-1">{{ exp.description }}</div>
      </el-timeline-item>
    </el-timeline>
  </div>

  <!-- 技能 -->
  <div v-if="fields.skills?.length" class="mt-5">
    <h4 class="text-sm font-medium text-gray-700 mb-2">技能标签</h4>
    <div class="flex flex-wrap gap-2">
      <el-tag
        v-for="(skill, idx) in fields.skills"
        :key="idx"
        size="small"
        effect="plain"
      >
        {{ skill }}
      </el-tag>
    </div>
  </div>
</template>
