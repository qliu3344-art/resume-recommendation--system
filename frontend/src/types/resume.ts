export interface WorkExperience {
  company: string
  position: string
  period: string
  description?: string
}

export interface ResumeUploadResponse {
  id: number
  filename: string
  status: ResumeStatus
  created_at: string
}

export interface ResumeFieldsOut {
  id: number
  resume_id: number
  name: string | null
  phone: string | null
  id_card: string | null
  email: string | null
  education: string | null
  school: string | null
  major: string | null
  graduation_year: number | null
  work_experience: WorkExperience[] | null
  skills: string[] | null
  is_duplicate: boolean
}

export interface ResumeDetailResponse {
  id: number
  filename: string
  status: ResumeStatus
  raw_text: string | null
  parsed_data: Record<string, unknown> | null
  fields: ResumeFieldsOut | null
  created_at: string
}

export interface ResumeListResponse {
  total: number
  items: ResumeUploadResponse[]
}

export interface ParseResponse {
  resume_id: number
  status: string
  fields: ResumeFieldsOut | null
  message: string
}

export type ResumeStatus = 'uploaded' | 'parsed' | 'verified'
