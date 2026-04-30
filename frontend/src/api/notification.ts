// src/api/notification.ts
import { apiClient } from '../services/http';
import type { AppNotification } from '../types'; // 引入我们写好的类型图纸

export const notificationApi = {
  // 提交手动录入的消息
  // 注意：入参里的 raw_content 已经根据你的新数据库改成了 content
  collect: async (payload: { sender: string; subject: string; content: string }) => {
    // 假设你的 collect 接口也迁移到了这个 prefix 下
    const { data } = await apiClient.post('/api/notifications/collect', payload);
    return data;
  },

  // 获取看板未处理消息列表 (对接后端的 /unsolved)
  getNotifications: async (): Promise<AppNotification[]> => {
    const { data } = await apiClient.get<AppNotification[]>('/api/notifications/unsolved');
    return data;
  },

  // 获取历史记录列表
  getHistory: async (): Promise<AppNotification[]> => {
    const { data } = await apiClient.get<AppNotification[]>('/api/notifications/history');
    return data;
  },

  // 标记消息为已处理
  markAsDone: async (id: number) => {
    const { data } = await apiClient.patch(`/api/notifications/${id}/done`);
    return data;
  },

  // 从历史记录中恢复消息
  restoreNotification: async (id: number) => {
    const { data } = await apiClient.patch(`/api/notifications/${id}/restore`);
    return data;
  }
};