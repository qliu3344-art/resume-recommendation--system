<script setup lang="ts">
import { reactive } from 'vue'
import type { JobCreate } from '@/types/job'

const form = reactive<JobCreate>({
  title: '',
  description: '',
  requirements: {
    min_education: '',
    min_years: 0,
    required_skills: [],
  },
})

defineExpose({ form })

const educationOptions = [
  { label: '专科', value: '专科' },
  { label: '本科', value: '本科' },
  { label: '硕士', value: '硕士' },
  { label: '博士', value: '博士' },
]

const skillOptions = [
  'Python', 'Java', 'JavaScript', 'TypeScript', 'Go', 'C++', 'Rust',
  'React', 'Vue.js', 'Node.js', 'Django', 'Flask', 'FastAPI',
  'MySQL', 'PostgreSQL', 'Redis', 'MongoDB',
  'Docker', 'Kubernetes', 'AWS', 'Linux',
  'TensorFlow', 'PyTorch', 'Pandas', 'NumPy',
  '产品设计', '用户研究', 'Figma', '项目管理', '敏捷开发', '数据分析', 'SQL',
]

const rules = {
  title: [{ required: true, message: '请输入岗位名称', trigger: 'blur' }],
}
</script>

<template>
  <el-form :model="form" :rules="rules" label-width="100px" class="max-w-2xl">
    <el-form-item label="岗位名称" prop="title">
      <el-input v-model="form.title" placeholder="如：高级后端开发工程师" />
    </el-form-item>

    <el-form-item label="岗位描述">
      <el-input
        v-model="form.description"
        type="textarea"
        :rows="4"
        placeholder="描述岗位职责和工作内容..."
      />
    </el-form-item>

    <el-divider content-position="left">招聘要求</el-divider>

    <el-form-item label="最低学历">
      <el-select v-model="form.requirements!.min_education" placeholder="不限" clearable class="w-48">
        <el-option v-for="o in educationOptions" :key="o.value" :label="o.label" :value="o.value" />
      </el-select>
    </el-form-item>

    <el-form-item label="最低工作年限">
      <el-input-number v-model="form.requirements!.min_years" :min="0" :max="20" class="w-48" />
      <span class="text-gray-400 text-xs ml-2">年</span>
    </el-form-item>

    <el-form-item label="必备技能">
      <el-select
        v-model="form.requirements!.required_skills"
        multiple
        filterable
        placeholder="请选择必备技能"
        class="w-full max-w-lg"
      >
        <el-option v-for="s in skillOptions" :key="s" :label="s" :value="s" />
      </el-select>
    </el-form-item>
  </el-form>
</template>
