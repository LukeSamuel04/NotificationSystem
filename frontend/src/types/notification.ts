// src/types/notification.ts

export interface AnalysisPayloadResponse {
  id: number;
  analysis_data: Record<string, any>;
  user_feedback_score?: number | null;
}

export interface EmailAnalysisResponse {
  id: number;
  priority_score: number;
  summary?: string;
  category?: string;
  category_id?: number;
}

export interface IMSessionStateResponse {
  priority_score: number;
  current_topic?: string;      // 💥 对齐后端真实字段
  summary_snapshot?: string;   // 💥 对齐后端真实字段
  is_read?: boolean;
}

export interface NotificationResponse {
  id: number;
  account_id: number;
  platform: 'email' | 'instagram';
  account_msg_id: string;
  status: string;

  sender?: string | null;
  external_sender_id?: string | null;
  subject?: string | null;
  cleaned_content?: string | null;

  is_from_me: boolean;
  reply_to_mid?: string | null;
  is_read?: boolean;

  email_analysis?: EmailAnalysisResponse | null;
  im_session_state?: IMSessionStateResponse | null; // 💥 核心修复：更正为真实的后端返回键名
  analysis_payload?: AnalysisPayloadResponse | null;

  received_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface GetNotificationsParams {
  status?: string;
  account_id?: string;
  is_read?: boolean;
  limit?: number;
  offset?: number;
}

export interface NotificationUpdatePayload {
  status?: string;
  is_read?: boolean;
}

export interface FeedbackUpdatePayload {
  user_feedback_score: number;
}

export interface GroupedNotification {
  id: string;
  platform: 'email' | 'instagram';
  account_id: number;
  external_sender_id?: string | null;
  messages: NotificationResponse[];
  latest_received_at: string;
  priority_score: number;
  title: string;
  is_read: boolean;
}