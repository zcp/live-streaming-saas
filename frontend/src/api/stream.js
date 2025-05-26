// frontend/src/api/stream.js
import axios from 'axios';
import { API_CONFIG } from './config';

const api = axios.create(API_CONFIG);

// 添加请求拦截器
api.interceptors.request.use(
  (config) => {
    // 在发送请求之前做些什么
    return config;
  },
  (error) => {
    // 对请求错误做些什么
    return Promise.reject(error);
  }
);

// 添加响应拦截器
api.interceptors.response.use(
  (response) => {
    // 对响应数据做点什么
    return response;
  },
  (error) => {
    // 对响应错误做点什么
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);



export const getStreams = async () => {
  try {
    const response = await api.get('/streams');
    return response.data;
  } catch (error) {
    console.error('获取直播流列表失败:', error);
    throw error;
  }
};


export const createStream = async (data) => {
  try {
    const response = await api.post('/streams', data);
    return response.data;
  } catch (error) {
    console.error('创建直播流失败:', error);
    throw error;
  }
};

export const updateStream = async (id, data) => {
  try {
    const response = await api.put(`/streams/${id}`, data);
    return response.data;
  } catch (error) {
    console.error('更新直播流失败:', error);
    throw error;
  }
};

export const deleteStream = async (id) => {
  try {
    const response = await api.delete(`/streams/${id}`);
    return response.data;
  } catch (error) {
    console.error('删除直播流失败:', error);
    throw error;
  }
};

// 更新流状态
// 更新流状态
// 添加推流相关的方法
export const startStreaming = async (streamId) => {
  try {
    const response = await api.post(`/streams/${streamId}/push`);
    return response.data;
  } catch (error) {
    console.error('开始推流失败:', error);
    throw error;
  }
};

export const stopStreaming = async (streamId) => {
  try {
    const response = await api.post(`/streams/${streamId}/stop`);
    return response.data;
  } catch (error) {
    console.error('停止推流失败:', error);
    throw error;
  }
};

export const updateStreamStatus = async (streamId, data) => {
  try {
    const response = await api.put(`/streams/${streamId}/status`, data);
    return response.data;
  } catch (error) {
    console.error('更新流状态失败:', error);
    throw error;
  }
};

// 获取流状态
export const getStreamStatus = async (streamId) => {
  try {
    const response = await api.get(`/streams/${streamId}/status`);
    return response.data;
  } catch (error) {
    console.error('获取流状态失败:', error);
    throw error;
  }
};
// 导出所有 API 方法
export const streamApi = {
  createStream,
  getStreams,
  updateStream,
  deleteStream,
  updateStreamStatus,
  getStreamStatus
}

// 默认导出
export default streamApi
