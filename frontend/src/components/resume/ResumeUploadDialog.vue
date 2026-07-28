<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadFile, UploadRawFile } from 'element-plus'

defineProps<{
  visible: boolean
  uploading: boolean
}>()

defineEmits<{
  'update:visible': [value: boolean]
  upload: [file: File]
}>()

const fileList = ref<UploadFile[]>([])

const allowedTypes = ['.pdf', '.docx', '.doc']

function beforeUpload(rawFile: UploadRawFile) {
  const ext = '.' + rawFile.name.split('.').pop()?.toLowerCase()
  if (!allowedTypes.includes(ext)) {
    ElMessage.error('仅支持 PDF 和 Word 格式')
    return false
  }
  if (rawFile.size > 20 * 1024 * 1024) {
    ElMessage.error('文件大小不能超过 20MB')
    return false
  }
  return true
}

function handleUpload(file: UploadFile) {
  if (file.raw) {
    // el-upload auto-upload=false, we handle via parent
    // This component only validates; parent handles the actual upload
  }
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="上传简历"
    width="520px"
    :close-on-click-modal="false"
  >
    <el-upload
      v-model:file-list="fileList"
      drag
      :auto-upload="false"
      :limit="1"
      :before-upload="beforeUpload"
      accept=".pdf,.docx,.doc"
      class="mx-auto"
    >
      <el-icon class="text-4xl text-gray-300 mb-3"><UploadFilled /></el-icon>
      <div class="text-sm text-gray-600">
        将简历文件拖到此处，或 <em class="text-primary not-italic">点击上传</em>
      </div>
      <template #tip>
        <div class="text-xs text-gray-400 mt-2">
          支持 PDF / Word 格式，单个文件不超过 20MB
        </div>
      </template>
    </el-upload>
    <template #footer>
      <el-button @click="$emit('update:visible', false)">取消</el-button>
      <el-button
        type="primary"
        :loading="uploading"
        :disabled="fileList.length === 0"
        @click="() => {
          if (fileList[0]?.raw) {
            $emit('upload', fileList[0].raw)
          }
        }"
      >
        开始上传
      </el-button>
    </template>
  </el-dialog>
</template>
