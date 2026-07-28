import { shallowRef } from 'vue'
import { jobApi } from '@/api/job'
import type { JobOut } from '@/types/job'

export function useJobs() {
  const items = shallowRef<JobOut[]>([])
  const total = shallowRef(0)
  const loading = shallowRef(false)
  const page = shallowRef(1)
  const pageSize = shallowRef(50)

  async function fetch() {
    loading.value = true
    try {
      const skip = (page.value - 1) * pageSize.value
      const res = await jobApi.list(skip, pageSize.value)
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

  return { items, total, loading, page, pageSize, fetch, onPageChange }
}
