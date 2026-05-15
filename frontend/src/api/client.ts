// src/api/client.ts
import axios from 'axios';

// 统一配置基础 Axios 实例
export const apiClient = axios.create({
  // 💥 注意这里加了 /api 后缀！因为后端的路由总线挂载在 /api 下
  baseURL: 'http://localhost:8000/api',
  timeout: 15000,
});

// 添加响应拦截器 (全局错误处理)
apiClient.interceptors.response.use(
  (response) => {
    // 2xx 范围内的状态码都会触发该函数。直接返回 data，脱掉 axios 的外壳
    return response.data;
  },
  (error) => {
    // 超出 2xx 范围的状态码都会触发该函数。
    console.error('🚨 全局 API 错误拦截:', error.response?.data || error.message);
    // 这里未来可以接 ui 库的 Toast，比如: toast.error(error.response.data.detail)
    return Promise.reject(error);
  }
);