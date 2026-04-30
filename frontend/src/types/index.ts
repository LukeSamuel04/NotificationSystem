// src/types/index.ts

export * from './account';
export * from './notification';
export interface Notification {
  id: number;
  sender: string;
  subject: string;
  raw_content: string;
  priority_score: number;
  category: string;
  created_at: string;
  status: 'unread' | 'read' | 'done';
}