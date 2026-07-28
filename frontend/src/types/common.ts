export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

export interface ApiError {
  detail: string
}
