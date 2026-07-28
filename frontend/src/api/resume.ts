import client from './client'
import type {
  ResumeUploadResponse,
  ResumeDetailResponse,
  ResumeListResponse,
  ParseResponse,
  ResumeFieldsOut,
} from '@/types/resume'

export const resumeApi = {
  upload(file: File) {
    const form = new FormData()
    form.append('file', file)
    return client.post<ResumeUploadResponse>('/resumes/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list(skip = 0, limit = 20) {
    return client.get<ResumeListResponse>('/resumes', { params: { skip, limit } })
  },

  detail(id: number) {
    return client.get<ResumeDetailResponse>(`/resumes/${id}`)
  },

  parse(id: number) {
    return client.post<ParseResponse>(`/resumes/${id}/parse`)
  },

  getDesensitized(id: number) {
    return client.get<ResumeFieldsOut>(`/resumes/${id}/desensitized`)
  },
}
