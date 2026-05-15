// src/types/account.ts

// 1. 平台枚举类型 (严格限制只能是这两种)
export type PlatformType = 'email' | 'instagram';

// 2. 各平台专属配置 (Config 碎片)
export interface EmailConfig {
  host?: string;
  port?: number;
  secure?: boolean;
  password?: string; // 💥 注意：后端返回时可能是 "********"，更新时需要特殊处理
  [key: string]: any; // 兜底其他可能存在的字段
}

export interface InstagramConfig {
  access_token?: string; // 💥 后端返回时可能被截断为 "EAAXXXX..."
  proxy_url?: string;
  [key: string]: any;
}

// 联合类型，方便前端表单根据平台推导字段
export type AccountConfig = EmailConfig | InstagramConfig;

// ==========================================
// 3. 核心接口：后端返回的完整账号对象 (对应 AccountResponse)
// ==========================================
export interface AccountResponse {
  id: string;                // 💥 已经与后端对齐，改为 string
  platform: PlatformType;
  platform_account_id: string;
  username: string;
  is_active: boolean;
  is_valid: boolean;         // 探针状态（绿灯/红灯）
  config: AccountConfig;     // 经过脱敏处理的配置
  //created_at: string;
}

// ==========================================
// 4. 表单提交载荷 (对应后端的入参 Schema)
// ==========================================

// 新建账号时的 Payload
export interface AccountCreatePayload {
  platform: PlatformType;
  platform_account_id: string; // 邮箱就是邮箱地址，IG 就是 Meta ID
  username: string;
  is_active: boolean;
  config: AccountConfig;       // 必须是明文的真实密码/Token
}

// 修改账号时的增量 Payload (所有字段可选)
export interface AccountUpdatePayload {
  username?: string;
  is_active?: boolean;
  config?: AccountConfig;
}