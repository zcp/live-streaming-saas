<!-- frontend/src/components/StreamCreate.vue -->
<template>
  <div class="stream-create">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      @submit.prevent="handleSubmit"
    >
      <el-form-item label="标题" prop="title">
        <el-input v-model="form.title" placeholder="请输入直播标题" />
      </el-form-item>

      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          placeholder="请输入直播描述"
        />
      </el-form-item>

      <el-form-item label="是否私有" prop="is_private">
        <el-switch v-model="form.is_private" />
      </el-form-item>

      <el-form-item label="是否录制" prop="is_recorded">
        <el-switch v-model="form.is_recorded" />
      </el-form-item>

      <el-form-item label="区域" prop="region">
        <el-select v-model="form.region" placeholder="请选择区域">
          <el-option label="杭州" value="cn-hangzhou" />
          <el-option label="上海" value="cn-shanghai" />
        </el-select>
      </el-form-item>

      <el-form-item label="存储类型" prop="storage_type">
        <el-select v-model="form.storage_type" placeholder="请选择存储类型">
          <el-option label="阿里云" value="aliyun" />
          <el-option label="AWS" value="aws" />
          <el-option label="本地" value="local" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" native-type="submit" :loading="loading">
          创建
        </el-button>
        <el-button @click="$emit('cancel')">取消</el-button>
      </el-form-item>
    </el-form>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { createStream } from '@/api/stream'
import { ElMessage } from 'element-plus'

export default {
  name: 'StreamCreate',
  emits: ['created', 'cancel'],
  setup(props, { emit }) {
    const formRef = ref(null)
    const loading = ref(false)

    const form = reactive({
      title: '',
      description: '',
      is_private: false,
      is_recorded: true,
      region: 'cn-hangzhou',
      storage_type: 'aliyun',
      provider: 'aliyun'
    })

    const rules = {
      title: [
        { required: true, message: '请输入直播标题', trigger: 'blur' },
        { min: 2, max: 100, message: '长度在 2 到 100 个字符', trigger: 'blur' }
      ],
      description: [
        { required: true, message: '请输入直播描述', trigger: 'blur' }
      ],
      region: [
        { required: true, message: '请选择区域', trigger: 'change' }
      ],
      storage_type: [
        { required: true, message: '请选择存储类型', trigger: 'change' }
      ]
    }

    const handleSubmit = async () => {
      if (!formRef.value) return

      try {
        await formRef.value.validate()
        loading.value = true

        const response = await createStream(form)
        ElMessage.success('创建成功')
        emit('created', response)
      } catch (error) {
        console.error('创建直播失败:', error)
        ElMessage.error(error.response?.data?.detail || '创建失败')
      } finally {
        loading.value = false
      }
    }

    return {
      formRef,
      form,
      rules,
      loading,
      handleSubmit
    }
  }
}
</script>

<style scoped>
.stream-create {
  padding: 20px;
}
</style>
