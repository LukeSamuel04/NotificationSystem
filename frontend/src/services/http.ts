// src/api/http.ts
import axios from 'axios';
// 统一配置基础 Axios 实例
export const apiClient = axios.create({
  // 根据你之前的截图，保持 8000 端口
  baseURL: 'http://localhost:8000',
  timeout: 15000, // 考虑到拉取邮件可能需要时间，超时设为 15 秒比较稳妥
});