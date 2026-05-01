from pydantic import BaseModel, Field
from typing import Optional, Union, Literal, Dict, Any
from typing_extensions import Annotated
from datetime import datetime

# -----------------------------------
# 0. 账号激活/停用快速配置端口
# -----------------------------------
class AccountToggle(BaseModel):
    is_active: bool

# -----------------------------------
# 1. 平台专属的配置子图纸 (Config Schemas)
# -----------------------------------
class EmailConfig(BaseModel):
    host: str
    port: Optional[int] = 993
    secure: Optional[bool] = True

class InstagramConfig(BaseModel):
    proxy_url: Optional[str] = None
    session_id: Optional[str] = None

class WhatsAppConfig(BaseModel):
    api_key: str

# 🆕 为更新操作准备的配置模型 (所有字段设为 Optional)
class EmailConfigUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    secure: Optional[bool] = None

class InstagramConfigUpdate(BaseModel):
    proxy_url: Optional[str] = None
    session_id: Optional[str] = None

class WhatsAppConfigUpdate(BaseModel):
    api_key: Optional[str] = None

# -----------------------------------
# 2. 派生各个平台的专属账号载荷 (Create)
# -----------------------------------
class AccountCreateBase(BaseModel):
    username: str
    password: str
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

# -----------------------------------
# 3. 💥 新增：更新载荷 (Update)
# -----------------------------------
# 用于修复 ImportError: cannot import name 'AccountUpdate'
class AccountUpdateBase(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None

class EmailAccountUpdate(AccountUpdateBase):
    platform: Literal["email"]
    config: Optional[EmailConfigUpdate] = None

class InstagramAccountUpdate(AccountUpdateBase):
    platform: Literal["instagram"]
    config: Optional[InstagramConfigUpdate] = None

class WhatsAppAccountUpdate(AccountUpdateBase):
    platform: Literal["whatsapp"]
    config: Optional[WhatsAppConfigUpdate] = None

# -----------------------------------
# 4. 辨析联合类型 (分拣器)
# -----------------------------------
AccountCreate = Annotated[
    Union[EmailAccountCreate, InstagramAccountCreate, WhatsAppAccountCreate],
    Field(discriminator="platform")
]

# 🆕 更新操作的分拣器
AccountUpdate = Annotated[
    Union[EmailAccountUpdate, InstagramAccountUpdate, WhatsAppAccountUpdate],
    Field(discriminator="platform")
]

# -----------------------------------
# 5. 响应标准 (回显给前端)
# -----------------------------------
class AccountResponse(BaseModel):
    id: int
    platform: str
    username: str
    # 💥 安全围栏：is_valid 仅在这里出现，确保用户不能通过接口篡改探针结果
    is_valid: bool
    is_active: bool
    config: Dict[str, Any]
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True