// src/types/preference.ts

// 基础基因
export interface UserPreferenceBase {
  platform: 'email' | 'instagram' | 'global';
  preference_type: 'sender_id' | 'topic' | 'email_domain';
  target_value: string;
  preference_factor: number;
}

// 接收后端的响应结构
export interface UserPreferenceResponse extends UserPreferenceBase {
  id: number;
  account_id: string;
}

// 发送给后端的新增载荷
export interface UserPreferenceCreate extends UserPreferenceBase {
  account_id: string;
}

// 发送给后端的修改载荷 (全选填)
export interface UserPreferenceUpdate {
  target_value?: string;
  preference_factor?: number;
}