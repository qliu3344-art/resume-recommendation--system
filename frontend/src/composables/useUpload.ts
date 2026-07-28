import { ref } from 'vue'
import { resumeApi } from '@/api/resume'
import type { ResumeUploadResponse } from '@/types/resume'

export function useUpload() {
  const uploading = ref(false)
  const uploaded = ref<ResumeUploadResponse | null>(null)

  async function upload(file: File) {
    uploading.value = true
    uploaded.value = null
    const result = await resumeApi.upload(file)
    uploaded.value = result
    uploading.value = false
    return result
  }

  return { uploading, uploaded, upload }
}
