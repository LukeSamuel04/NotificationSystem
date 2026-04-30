// src/types/notification.ts

export interface AppNotification {
  // === 原始消息字段 (来自 raw_notifications 表) ===
  id: number;
  account_id: number;        // [新增] 关联的抓取账号ID
  account_msg_id: string;    // [新增] 平台原本的消息ID (去重用)
  sender: string;
  subject: string;
  cleaned_content: string;           // [修改] 截图里叫 content，原来叫 raw_content
  status: 'unread' | 'read' | 'done';
  // === 时间戳字段 ===
  received_at?: string;
  created_at?: string;
  updated_at?: string;  // [新增]
  // === AI 分析字段 (来自 notification_analysis 表) ===
  // 注意：这里我加了 `?` (可选属性)。
  // 因为消息刚抓取时，AI 可能还没打分，这些字段可能是 null 或 undefined
  priority_score?: number;   // 优先级评分
  category?: string;         // 分类
  summary?: string;          // [新增] AI 生成的摘要
}