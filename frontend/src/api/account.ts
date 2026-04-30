// src/api/account.ts
import { apiClient } from '../services/http';
import type { AccountCreatePayload, AccountResponse } from '../types/account';

export const accountApi = {
  // 获取所有绑定的账号列表
  getAccounts: async (): Promise<AccountResponse[]> => {
    const { data } = await apiClient.get<AccountResponse[]>('/api/accounts/');
    return data;
  },

  // 新增绑定账号（触发后端防御性探针）
  createAccount: async (payload: AccountCreatePayload): Promise<AccountResponse> => {
    const { data } = await apiClient.post<AccountResponse>('/api/accounts/', payload);
    return data;
  },

  // 更新现有账号配置（触发重新验证）
  updateAccount: async (id: number, payload: AccountCreatePayload): Promise<AccountResponse> => {
    const { data } = await apiClient.put<AccountResponse>(`/api/accounts/${id}`, payload);
    return data;
  },

  // 解除绑定账号
  deleteAccount: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/accounts/${id}`);
  }
};