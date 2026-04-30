//src/types/account.ts
/**
 * 1. 基础账号接口 (所有平台共有的属性)
 */
export interface BaseAccount {
  username: string;
  password: string;    // 对应授权码、API Key 或登录凭证
  is_active?: boolean;
}

/**
 * 2. 平台专有配置 (Config 碎片)
 */
export interface EmailConfig {
  host: string;        // IMAP 服务器地址
  port?: number;
}

export interface InstagramConfig {
  proxy_url?: string;
  session_id?: string;
}

// 💥 新增：WhatsApp 专有配置
export interface WhatsAppConfig {
  api_key?: string;    // 如果使用官方 API
  phone_number_id?: string;
  session_data?: string; // 如果是基于 Web 协议的 Session 挂载
}

/**
 * 3. 平台子类 (继承基类并绑定专有 Config)
 */
export interface EmailAccount extends BaseAccount {
  platform: 'email';
  config: EmailConfig;
}

export interface InstagramAccount extends BaseAccount {
  platform: 'instagram';
  config: InstagramConfig;
}

// 💥 新增：WhatsApp 子类
export interface WhatsAppAccount extends BaseAccount {
  platform: 'whatsapp';
  config: WhatsAppConfig;
}

/**
 * 4. 辨析联合类型 (万能载荷)
 * 增加 WhatsAppAccount 后，这个联合类型现在支持三大平台
 */
export type AccountCreatePayload =
  | EmailAccount
  | InstagramAccount
  | WhatsAppAccount;

/**
 * 5. 后端返回结果
 */
export interface AccountResponse {
  id: number;
  platform: 'email' | 'instagram' | 'whatsapp';
  username: string;
  is_active: boolean;
  // 数据库存储的 JSON 字段
  config: EmailConfig | InstagramConfig | WhatsAppConfig;
  created_at?: string;
}