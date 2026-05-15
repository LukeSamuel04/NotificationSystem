// src/api/account.ts
import { apiClient } from './client';
import type {
  AccountResponse,
  AccountCreatePayload,
  AccountUpdatePayload
} from '../types/account';

/**
 * 账号资产 API 集合
 * 对应后端的 /api/accounts 路由
 */
export const accountApi = {
  // 1. 获取所有绑定的账号列表
  getAccounts: async (): Promise<AccountResponse[]> => {
    // apiClient 已经配置了 baseURL，所以这里直接写 '/' 即可
    // 实际请求地址: GET http://localhost:8000/api/accounts/
    return apiClient.get('/accounts/');
  },

  // 2. 新增账号 (会触发后端探针验证)
  createAccount: async (data: AccountCreatePayload): Promise<AccountResponse> => {
    return apiClient.post('/accounts/', data);
  },

  // 3. 更新账号 (增量更新，按需触发探针)
  updateAccount: async (id: string, data: AccountUpdatePayload): Promise<AccountResponse> => {
    return apiClient.put(`/accounts/${id}`, data);
  },

  // 4. 彻底删除账号并解绑 Meta 授权
  deleteAccount: async (id: string): Promise<{ message: string }> => {
    return apiClient.delete(`/accounts/${id}`);
  },

  // 5. 快速启用/停用开关 (不触发探针)
  toggleAccount: async (id: string, isActive: boolean): Promise<AccountResponse> => {
    return apiClient.patch(`/accounts/${id}/toggle`, { is_active: isActive });
  }
};