<template>
  <div class="stream-push">
    <div class="push-info">
      <h3>推流信息</h3>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="推流地址">
          <div class="copy-wrapper">
            {{ pushUrl }}
            <el-button type="primary" link @click="copyPushUrl">
              复制
            </el-button>
          </div>
        </el-descriptions-item>
        <el-descriptions-item label="推流密钥">
          <div class="copy-wrapper">
            {{ streamKey }}
            <el-button type="primary" link @click="copyStreamKey">
              复制
            </el-button>
          </div>
        </el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="push-actions">
      <el-button
        type="primary"
        @click="startStream"
        :loading="loading"
        :disabled="isStreaming"
      >
        开始推流
      </el-button>
      <el-button
        type="danger"
        @click="stopStream"
        :disabled="!isStreaming"
      >
        停止推流
      </el-button>
    </div>

    <div class="push-tips">
      <h4>推流说明：</h4>
      <p>1. 使用 OBS 或其他推流软件</p>
      <p>2. 设置推流地址：{{ pushUrl }}</p>
      <p>3. 设置推流密钥：{{ streamKey }}</p>
      <p>4. 点击开始推流</p>
      <p>5. 或者使用 FFmpeg 命令：</p>
      <p>ffmpeg -re -i 视频文件路径 -c copy -f flv {{ pushUrl }}</p>
    </div>
  </div>
</template>

<script>
import { ref, computed, onUnmounted } from 'vue'
import { updateStreamStatus } from '@/api/stream'
import { ElMessage } from 'element-plus'
import axios from 'axios'

export default {
  name: 'StreamPush',
  props: {
    streamId: {
      type: String,
      required: true
    },
    streamKey: {
      type: String,
      required: true
    }
  },
  emits: ['stream-started', 'stream-ended'],
  setup(props, { emit }) {
    const loading = ref(false)
    const isStreaming = ref(false)
    let statusCheckInterval = null

    const pushUrl = computed(() => {
      // 确保推流地址格式与 FFmpeg 命令完全一致
      return `rtmp://124.220.235.226:1935/live/${props.streamKey}`
    })

    const copyPushUrl = () => {
      navigator.clipboard.writeText(pushUrl.value)
      ElMessage.success('推流地址已复制')
    }

    const copyStreamKey = () => {
      navigator.clipboard.writeText(props.streamKey)
      ElMessage.success('推流密钥已复制')
    }

    const startStream = async () => {
      try {
        loading.value = true

        // 调用后端开始推流 API
        console.log("开始推流1")
        const response = await axios.post(`/api/v1/streams/${props.streamId}/push`)
        console.log("开始推流2")

        // 检查响应数据
        if (response.data && response.data.message === "success") {  // 修改这里
          isStreaming.value = true
          emit('stream-started')
          ElMessage.success('推流已开始')
        } else {
          throw new Error(response.data?.message || '推流启动失败')
        }
      } catch (error) {
        console.error('开始推流失败:', error)
        ElMessage.error('开始推流失败：' + (error.response?.data?.detail || error.message))  // 修改这里，使用 detail 而不是 message
      } finally {
        loading.value = false
      }
    }

    const stopStream = async () => {
      try {
        loading.value = true

        // 调用后端停止推流 API
        const response = await axios.post(`/api/v1/streams/${props.streamId}/stop`)

        if (response.data.success) {
          isStreaming.value = false
          emit('stream-ended')
          ElMessage.success('推流已停止')
        } else {
          throw new Error(response.data.message || '停止推流失败')
        }
      } catch (error) {
        console.error('停止推流失败:', error)
        ElMessage.error('停止推流失败：' + (error.response?.data?.message || error.message))
      } finally {
        loading.value = false
      }
    }

    // 定期检查推流状态
    const checkStreamStatus = async () => {
      if (isStreaming.value) {
        try {
          const response = await axios.get(`/api/v1/streams/${props.streamId}/push-status`)
          if (!response.data.is_streaming) {
            isStreaming.value = false
            emit('stream-ended')
            ElMessage.warning('推流已断开')
          }
        } catch (error) {
          console.error('检查推流状态失败:', error)
        }
      }
    }

    // 每 10 秒检查一次推流状态
    statusCheckInterval = setInterval(checkStreamStatus, 10000)

    // 组件卸载时清理定时器
    onUnmounted(() => {
      if (statusCheckInterval) {
        clearInterval(statusCheckInterval)
      }
    })

    return {
      loading,
      isStreaming,
      pushUrl,
      startStream,
      stopStream,
      copyPushUrl,
      copyStreamKey
    }
  }
}
</script>

<style scoped>
.stream-push {
  padding: 20px;
}

.push-info {
  margin-bottom: 20px;
}

.push-actions {
  margin: 20px 0;
  display: flex;
  gap: 10px;
}

.push-tips {
  margin-top: 20px;
  padding: 15px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.push-tips h4 {
  margin-top: 0;
  margin-bottom: 10px;
}

.push-tips p {
  margin: 5px 0;
  color: #666;
}

.copy-wrapper {
  display: flex;
  align-items: center;
  gap: 10px;
}
</style>
