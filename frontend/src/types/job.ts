export interface JobRequirements {
  min_education?: string
  min_years?: number
  required_skills?: string[]
}

export interface JobCreate {
  title: string
  description?: string | null
  requirements?: JobRequirements | null
}

export interface JobUpdate {
  title?: string | null
  description?: string | null
  requirements?: JobRequirements | null
}

export interface JobOut {
  id: number
  title: string
  description: string | null
  requirements: JobRequirements | null
  created_at: string
}

export interface JobListResponse {
  total: number
  items: JobOut[]
}

export interface MatchResult {
  resume_id: number
  name: string | null
  keyword_score: number
  semantic_score: number
  total_score: number
  match_details: Record<string, unknown> | null
}

export interface MatchResponse {
  job_id: number
  job_title: string
  total_matches: number
  results: MatchResult[]
}
