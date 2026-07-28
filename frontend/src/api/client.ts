import axios, { type AxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'

const instance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' },
})

instance.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail ?? error.message ?? '请求失败，请检查网络连接'
    ElMessage.error(message)
    return Promise.reject(error)
  },
)

/**
 * 类型安全的 HTTP 客户端。
 * 拦截器已将 AxiosResponse 解包为 response.data，
 * 因此所有方法的返回类型直接是 T 而非 AxiosResponse<T>。
 */
const client = {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as Promise<T>
  },
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config) as Promise<T>
  },
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config) as Promise<T>
  },
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config) as Promise<T>
  },
}

export default client
