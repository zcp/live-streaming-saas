<template>
  <div class="home-view">
    <div class="header">
      <h1>直播流列表</h1>
      <el-button type="primary" @click="showCreateDialog">创建直播</el-button>
    </div>

    <div v-if="loading">加载中...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <el-row :gutter="20">
        <el-col :span="8" v-for="stream in streams" :key="stream.id">
          <el-card class="stream-card">
            <template #header>
              <div class="card-header">
                <h3>{{ stream.title }}</h3>
                <div class="stream-status">
                  <el-tag :type="getStatusType(stream.status)">
                    {{ stream.status }}
                  </el-tag>
                </div>
              </div>
            </template>

            <div class="stream-info">
              <p>{{ stream.description }}</p>
              <div class="stream-actions">
                <el-button
                  type="primary"
                  @click="showPushDialog(stream)"
                  :disabled="stream.status === 'streaming'"
                >
                  {{ stream.status === 'streaming' ? '直播中' : '开始直播' }}
                </el-button>
                <el-button
                  type="danger"
                  @click="deleteStream(stream.id)"
                >
                  删除
                </el-button>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 创建直播对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建直播"
      width="500px"
    >
      <stream-create
        @created="handleStreamCreated"
        @cancel="createDialogVisible = false"
      />
    </el-dialog>

    <!-- 推流对话框 -->
    <el-dialog
      v-model="pushDialogVisible"
      title="推流"
      width="800px"
    >
      <stream-push
        v-if="selectedStream"
        :stream-id="selectedStream.id"
        :stream-key="selectedStream.stream_key"
        @stream-started="handleStreamStarted"
        @stream-ended="handleStreamEnded"
      />
    </el-dialog>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { getStreams, deleteStream } from '@/api/stream'
import StreamCreate from '../components/StreamCreate.vue'
import StreamPush from '../components/StreamPush.vue'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'HomeView',
  components: {
    StreamCreate,
    StreamPush
  },
  setup() {
    const streams = ref([])
    const loading = ref(true)
    const error = ref(null)
    const createDialogVisible = ref(false)
    const pushDialogVisible = ref(false)
    const selectedStream = ref(null)

    // 获取直播列表
    const fetchStreams = async () => {
      try {
        loading.value = true
        const response = await getStreams()
        if (response.message === 'success') {
          streams.value = response.data
          error.value = null
        } else {
          error.value = '获取直播流列表失败'
        }
      } catch (err) {
        error.value = '获取直播流列表失败'
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    // 显示创建对话框
    const showCreateDialog = () => {
      createDialogVisible.value = true
    }

    // 处理创建成功
    const handleStreamCreated = async (stream) => {
      createDialogVisible.value = false
      await fetchStreams()
      ElMessage.success('创建成功')
    }

    // 显示推流对话框
    const showPushDialog = (stream) => {
      selectedStream.value = stream
      pushDialogVisible.value = true
    }

    // 处理推流开始
    const handleStreamStarted = async () => {
      await fetchStreams()
      ElMessage.success('直播已开始')
    }

    // 处理推流结束
    const handleStreamEnded = async () => {
      await fetchStreams()
      ElMessage.success('直播已结束')
    }

    // 删除直播
    const handleDeleteStream = async (id) => {
      try {
        await ElMessageBox.confirm('确定要删除这个直播吗？', '提示', {
          type: 'warning'
        })
        await deleteStream(id)
        await fetchStreams()
        ElMessage.success('删除成功')
      } catch (err) {
        if (err !== 'cancel') {
          console.error('删除直播流失败:', err)
          ElMessage.error('删除失败')
        }
      }
    }

    // 获取状态标签类型
    const getStatusType = (status) => {
      const types = {
        created: 'info',
        scheduled: 'warning',
        streaming: 'success',
        paused: 'warning',
        ended: 'info',
        error: 'danger'
      }
      return types[status] || 'info'
    }

    onMounted(() => {
      fetchStreams()
    })

    return {
      streams,
      loading,
      error,
      createDialogVisible,
      pushDialogVisible,
      selectedStream,
      showCreateDialog,
      handleStreamCreated,
      showPushDialog,
      handleStreamStarted,
      handleStreamEnded,
      deleteStream: handleDeleteStream,
      getStatusType
    }
  }
}
</script>

<style scoped>
.home-view {
  padding: 20px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.stream-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stream-info {
  min-height: 100px;
}

.stream-actions {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}

.stream-status {
  margin-left: 10px;
}
</style>
