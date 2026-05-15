// src/api/preference.ts
import { apiClient } from './client';
import type {
  UserPreferenceResponse,
  UserPreferenceCreate,
  UserPreferenceUpdate
} from '@/types/preference';

export const preferenceApi = {
  getPreferences: async (accountId: string, platform?: string): Promise<UserPreferenceResponse[]> => {
    // 💥 修复：取消 { data } 解构，直接 return 拦截器吐出的真实数据
    return await apiClient.get('/preferences', {
      params: { account_id: accountId, platform }
    });
  },

  createPreference: async (payload: UserPreferenceCreate): Promise<UserPreferenceResponse> => {
    // 💥 修复：取消解构
    return await apiClient.post('/preferences', payload);
  },

  updatePreference: async (id: number, payload: UserPreferenceUpdate): Promise<UserPreferenceResponse> => {
    // 💥 修复：取消解构
    return await apiClient.patch(`/preferences/${id}`, payload);
  },

  deletePreference: async (id: number): Promise<void> => {
    await apiClient.delete(`/preferences/${id}`);
  }
};