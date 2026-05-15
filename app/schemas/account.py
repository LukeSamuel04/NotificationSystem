# app/schemas/account.py
from pydantic import BaseModel, Field
from typing import Optional, Union, Literal, Dict, Any
from typing_extensions import Annotated
from datetime import datetime

# --------------------------------------------------------------------------
# 0. 原子化的小功能交互模型 (Atomic Models)
# --------------------------------------------------------------------------

class AccountToggle(BaseModel):
    """用于快速切换账号激活状态的极简载荷"""
    is_active: bool


# --------------------------------------------------------------------------
# 1. 平台专属配置图纸 (Platform Specific Configs)
# --------------------------------------------------------------------------

class EmailConfig(BaseModel):
    """Email (IMAP) 核心配置逻辑"""
    host: str
    port: Optional[int] = 993
    secure: Optional[bool] = True
    password: str  # 存储邮件授权码或登录密码

class InstagramConfig(BaseModel):
    """
    Instagram (Meta Graph API) 配置
    """
    access_token: str  # Meta 长期访问令牌 (必备)
    proxy_url: Optional[str] = None
    session_id: Optional[str] = None

class WhatsAppConfig(BaseModel):
    """WhatsApp Business API 配置"""
    api_key: str


# --------------------------------------------------------------------------
# 2. 更新账号配置专用图纸 (Update Configs - All Optional)
# --------------------------------------------------------------------------

class EmailConfigUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    secure: Optional[bool] = None
    password: Optional[str] = None

class InstagramConfigUpdate(BaseModel):
    # 💥 [核心修复]：更新时允许增量修改 Token
    access_token: Optional[str] = None
    proxy_url: Optional[str] = None
    session_id: Optional[str] = None

class WhatsAppConfigUpdate(BaseModel):
    api_key: Optional[str] = None


# --------------------------------------------------------------------------
# 3. 账号创建载荷 (Create Schemas)
# --------------------------------------------------------------------------

class AccountCreateBase(BaseModel):
    """所有平台账号的公共属性"""
    platform_account_id: str  # 平台侧唯一标识 (如 IG Business ID 或 Email 地址)
    username: str             # 用户自定义的显示名称
    is_active: Optional[bool] = True

class EmailAccountCreate(AccountCreateBase):
    platform: Literal["email"]
    config: EmailConfig

class InstagramAccountCreate(AccountCreateBase):
    platform: Literal["instagram"]
    config: InstagramConfig

class WhatsAppAccountCreate(AccountCreateBase):
    platform: Literal["whatsapp"]
    config: WhatsAppConfig


# --------------------------------------------------------------------------
# 4. 账号更新载荷 (Update Schemas)
# --------------------------------------------------------------------------

class AccountUpdateBase(BaseModel):
    platform_account_id: Optional[str] = None
    username: Optional[str] = None
    is_active: Optional[bool] = None

class EmailAccountUpdate(AccountUpdateBase):
    platform: Literal["email"]
    config: Optional[EmailConfigUpdate] = None

class InstagramAccountUpdate(AccountUpdateBase):
    platform: Literal["instagram"]
    config: Optional[InstagramConfigUpdate] = None

class WhatsAppAccountUpdate(AccountUpdateBase):
    platform: Literal["whatsapp"] = "whatsapp"
    config: Optional[WhatsAppConfigUpdate] = None


# --------------------------------------------------------------------------
# 5. 辨析联合类型 (Type Discriminators)
# 💥 这里的逻辑是 FastAPI 路由能够根据 JSON 中的 "platform" 字段自动分发到对应类的关键
# --------------------------------------------------------------------------

AccountCreate = Annotated[
    Union[EmailAccountCreate, InstagramAccountCreate, WhatsAppAccountCreate],
    Field(discriminator="platform")
]

AccountUpdate = Annotated[
    Union[EmailAccountUpdate, InstagramAccountUpdate, WhatsAppAccountUpdate],
    Field(discriminator="platform")
]


# --------------------------------------------------------------------------
# 6. 统一响应标准 (Response Schema)
# --------------------------------------------------------------------------

class AccountResponse(BaseModel):
    """
    暴露给前端的账号模型
    包括：id，账号平台唯一id，平台，用户名，可用性，是否激活，具体设置，创建时间。
    """
    id: int
    platform_account_id: str
    platform: str
    username: str
    is_valid: bool   # 探针验证结果：True 表示连通性正常
    is_active: bool  # 用户手动开关：True 表示允许巡检
    config: Dict[str, Any]  # 以字典形式返回配置（脱敏逻辑建议在应用层处理）
    #created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  # 允许从 SQLAlchemy 模型对象直接转换