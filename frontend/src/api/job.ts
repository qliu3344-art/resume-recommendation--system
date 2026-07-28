import client from './client'
import type { JobCreate, JobUpdate, JobOut, JobListResponse } from '@/types/job'

export const jobApi = {
  create(data: JobCreate) {
    return client.post<JobOut>('/jobs', data)
  },

  list(skip = 0, limit = 50) {
    return client.get<JobListResponse>('/jobs', { params: { skip, limit } })
  },

  detail(id: number) {
    return client.get<JobOut>(`/jobs/${id}`)
  },

  update(id: number, data: JobUpdate) {
    return client.put<JobOut>(`/jobs/${id}`, data)
  },

  delete(id: number) {
    return client.delete(`/jobs/${id}`)
  },
}
