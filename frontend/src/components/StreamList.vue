<!-- frontend/src/components/StreamList.vue -->
<template>
  <div class="stream-list">
    <h2>直播流列表</h2>
    <div v-if="loading">加载中...</div>
    <div v-else-if="error">{{ error }}</div>
    <div v-else>
      <div v-for="stream in streams" :key="stream.id" class="stream-item">
        <h3>{{ stream.title }}</h3>
        <p>{{ stream.description }}</p>
        <div class="stream-actions">
          <button @click="viewStream(stream)">查看</button>
          <button @click="editStream(stream)">编辑</button>
          <button @click="deleteStream(stream.id)" class="delete-btn">删除</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { getStreams, deleteStream } from '@/api/stream';
import { ElMessage, ElMessageBox } from 'element-plus';

export default {
  name: 'StreamList',
  setup() {
    const router = useRouter();
    const streams = ref([]);
    const loading = ref(true);
    const error = ref(null);

// StreamList.vue
const fetchStreams = async () => {
  try {
    loading.value = true;
    const response = await getStreams();
    console.log('获取到的直播流列表:', response);

    // 使用 response.data 而不是 response.items
    if (response && response.data) {
      streams.value = response.data;
      console.log('设置后的streams:', streams.value);
    } else {
      console.warn('响应数据格式不正确:', response);
      streams.value = [];
    }
    error.value = null;
  } catch (err) {
    error.value = '获取直播流列表失败';
    console.error('获取直播流列表失败:', err);
    ElMessage.error('获取直播流列表失败');
  } finally {
    loading.value = false;
  }
};

    const viewStream = (stream) => {
      console.log('查看直播流:', stream);
      if (!stream || !stream.id) {
        ElMessage.error('无效的直播流ID');
        return;
      }
      router.push(`/streams/${stream.id}`);
    };

    const editStream = (stream) => {
      console.log('编辑直播流:', stream);
      if (!stream || !stream.id) {
        ElMessage.error('无效的直播流ID');
        return;
      }
      router.push(`/streams/${stream.id}/edit`);
    };

    const handleDeleteStream = async (id) => {
      try {
        // 添加确认对话框
        await ElMessageBox.confirm(
          '确认删除该直播流吗？',
          '提示',
          {
            confirmButtonText: '确定',
            cancelButtonText: '取消',
            type: 'warning'
          }
        );

        await deleteStream(id);
        ElMessage.success('删除成功');
        await fetchStreams();
      } catch (err) {
        if (err === 'cancel') {
          return;
        }
        console.error('删除直播流失败:', err);
        ElMessage.error('删除失败');
      }
    };

    onMounted(() => {
      fetchStreams();
    });

    return {
      streams,
      loading,
      error,
      viewStream,
      editStream,
      deleteStream: handleDeleteStream,
      fetchStreams
    };
  }
};
</script>

<style scoped>
.stream-list {
  padding: 20px;
}

.stream-item {
  border: 1px solid #ddd;
  padding: 15px;
  margin-bottom: 15px;
  border-radius: 8px;
  background-color: #fff;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.stream-item h3 {
  margin: 0 0 10px 0;
  color: #333;
}

.stream-item p {
  margin: 0 0 15px 0;
  color: #666;
}

.stream-actions {
  display: flex;
  gap: 10px;
}

button {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.3s;
}

button:not(.delete-btn) {
  background-color: #4CAF50;
  color: white;
}

button:not(.delete-btn):hover {
  background-color: #45a049;
}

.delete-btn {
  background-color: #f44336;
  color: white;
}

.delete-btn:hover {
  background-color: #da190b;
}
</style>
