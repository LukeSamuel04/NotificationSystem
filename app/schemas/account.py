from pydantic import BaseModel, Field
from typing import Optional, Union, Literal, Dict, Any
from typing_extensions import Annotated

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


# -----------------------------------
# 2. 派生各个平台的专属账号载荷
# -----------------------------------
# 💥 优化：把公共字段提取到父类，避免重复写 username, password, is_active
class AccountCreateBase(BaseModel):
    username: str
    password: str
    is_active: Optional[bool] = True  # 允许前端在创建/编辑时传递启停状态

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
# 3. 辨析联合类型 (分拣器)
# -----------------------------------
AccountCreate = Annotated[
    Union[EmailAccountCreate, InstagramAccountCreate, WhatsAppAccountCreate],
    Field(discriminator="platform")
]

# -----------------------------------
# 4. 响应标准 (回显给前端)
# -----------------------------------
class AccountResponse(BaseModel):
    id: int
    platform: str
    username: str
    is_valid: bool   # ✅ 你新增的系统健康状态
    is_active: bool  # ✅ 用户的启停意愿状态
    config: Dict[str, Any]

    class Config:
        from_attributes = True