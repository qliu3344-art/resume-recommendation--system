import { shallowRef } from 'vue'
import { matchApi } from '@/api/match'
import type { MatchResponse, MatchResult } from '@/types/job'

export function useMatch() {
  const results = shallowRef<MatchResult[]>([])
  const jobTitle = shallowRef('')
  const totalMatches = shallowRef(0)
  const loading = shallowRef(false)
  const runLoading = shallowRef(false)

  async function fetchResults(jobId: number) {
    loading.value = true
    try {
      const res = await matchApi.getResults(jobId)
      results.value = res.results
      jobTitle.value = res.job_title
      totalMatches.value = res.total_matches
    } finally {
      loading.value = false
    }
  }

  async function run(jobId: number, topK = 20) {
    runLoading.value = true
    const res = await matchApi.run(jobId, topK)
    results.value = res.results
    jobTitle.value = res.job_title
    totalMatches.value = res.total_matches
    runLoading.value = false
    return res
  }

  return { results, jobTitle, totalMatches, loading, runLoading, fetchResults, run }
}
