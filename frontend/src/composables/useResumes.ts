import { shallowRef } from 'vue'
import { resumeApi } from '@/api/resume'
import type { ResumeUploadResponse } from '@/types/resume'

export function useResumes() {
  const items = shallowRef<ResumeUploadResponse[]>([])
  const total = shallowRef(0)
  const loading = shallowRef(false)
  const page = shallowRef(1)
  const pageSize = shallowRef(20)

  async function fetch() {
    loading.value = true
    try {
      const skip = (page.value - 1) * pageSize.value
      const res = await resumeApi.list(skip, pageSize.value)
      items.value = res.items
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  function onPageChange(p: number) {
    page.value = p
    fetch()
  }

  function onPageSizeChange(size: number) {
    pageSize.value = size
    page.value = 1
    fetch()
  }

  return { items, total, loading, page, pageSize, fetch, onPageChange, onPageSizeChange }
}
