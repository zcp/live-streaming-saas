// frontend/src/api/config.js
export const API_BASE_URL = 'http://localhost:8083/api/v1';

export const API_CONFIG = {
  baseURL: API_BASE_URL,
  timeout: 5000,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: false  // 允许跨域请求携带凭证
};
