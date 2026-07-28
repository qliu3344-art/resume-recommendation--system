import { shallowRef } from 'vue'
import { resumeApi } from '@/api/resume'
import type { ResumeDetailResponse } from '@/types/resume'

export function useResumeDetail() {
  const resume = shallowRef<ResumeDetailResponse | null>(null)
  const loading = shallowRef(false)
  const parseLoading = shallowRef(false)
  const error = shallowRef('')

  async function fetch(id: number) {
    loading.value = true
    error.value = ''
    try {
      resume.value = await resumeApi.detail(id)
    } catch {
      error.value = '简历不存在或加载失败'
    } finally {
      loading.value = false
    }
  }

  async function parse(id: number) {
    parseLoading.value = true
    try {
      const result = await resumeApi.parse(id)
      // 解析成功后重新加载详情
      await fetch(id)
      return result
    } finally {
      parseLoading.value = false
    }
  }

  return { resume, loading, parseLoading, error, fetch, parse }
}
