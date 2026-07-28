import { shallowRef } from 'vue'
import { jobApi } from '@/api/job'
import type { JobOut, JobCreate, JobUpdate } from '@/types/job'

export function useJobDetail() {
  const job = shallowRef<JobOut | null>(null)
  const loading = shallowRef(false)
  const saveLoading = shallowRef(false)
  const error = shallowRef('')

  async function fetch(id: number) {
    loading.value = true
    error.value = ''
    try {
      job.value = await jobApi.detail(id)
    } catch {
      error.value = '岗位不存在或加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(data: JobCreate) {
    saveLoading.value = true
    const result = await jobApi.create(data)
    saveLoading.value = false
    return result
  }

  async function update(id: number, data: JobUpdate) {
    saveLoading.value = true
    const result = await jobApi.update(id, data)
    saveLoading.value = false
    return result
  }

  async function remove(id: number) {
    await jobApi.delete(id)
  }

  return { job, loading, saveLoading, error, fetch, create, update, remove }
}
