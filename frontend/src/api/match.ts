import client from './client'
import type { MatchResponse, MatchResult } from '@/types/job'

export const matchApi = {
  run(jobId: number, topK = 20) {
    return client.post<MatchResponse>(`/match/${jobId}`, null, { params: { top_k: topK } })
  },

  getResults(jobId: number) {
    return client.get<MatchResponse>(`/match/${jobId}/results`)
  },
}
