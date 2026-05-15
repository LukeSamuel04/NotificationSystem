// src/api/notification.ts
import { apiClient } from './client';
import type {
  NotificationResponse,
  GetNotificationsParams,
  NotificationUpdatePayload,
  FeedbackUpdatePayload
} from '../types/notification';

/**
 * AI 优先级看板 API 集合
 * 对应后端的 /api/notifications 路由
 */
export const notificationApi = {
  // 1. 核心看板列表接口 (大一统聚合器)
  getNotifications: async (params?: GetNotificationsParams): Promise<NotificationResponse[]> => {
    // GET /notifications/?status=processed&limit=50
    return apiClient.get('/notifications/', { params });
  },

  // 2. 局部更新接口 (状态流转 & 红点消除)
  // 支持标记已读、拖拽归档
  updateNotification: async (id: number, data: NotificationUpdatePayload): Promise<NotificationResponse> => {
    return apiClient.patch(`/notifications/${id}`, data);
  },

  // 3. 反馈飞轮接口 (人类干预算分)
  submitFeedback: async (id: number, score: number): Promise<{ status: string; message: string }> => {
    const payload: FeedbackUpdatePayload = { user_feedback_score: score };
    return apiClient.patch(`/notifications/${id}/feedback`, payload);
  },

  // 4. 批量已读 (用户体验增强)
  markAllAsRead: async (accountId: string): Promise<{ status: string; count: string }> => {
    return apiClient.post(`/notifications/mark-all-read/${accountId}`);
  }
};