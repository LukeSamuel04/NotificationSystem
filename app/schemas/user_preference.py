# app/schemas/user_preference.py
from pydantic import BaseModel, Field
from typing import Optional, Literal


# --------------------------------------------------------------------------
# 1. 基础规则基因 (Base Schema)
# --------------------------------------------------------------------------
class UserPreferenceBase(BaseModel):
    """
    用户偏好规则的基础字段。
    定义了：针对哪个平台、哪种类型、匹配什么值、给多少权重。
    """
    platform: str = Field(..., description="平台标识，如 'email', 'instagram' 或 'global'")
    preference_type: Literal["sender_id", "topic", "email_domain"] = Field(
        ..., description="匹配维度：发件人、话题关键词或域名"
    )
    target_value: str = Field(..., description="匹配的目标值 (如 'urgent', '@bth.se', 'gym_bro_id')")
    preference_factor: float = Field(
        ..., ge=0.0, le=10.0, description="权重因子：0.0 为屏蔽，1.0 为中性，>1.0 为提权"
    )


# --------------------------------------------------------------------------
# 2. 入站：创建/更新模具 (Create/Update Schema)
# 🛫 用户在前端点击“添加规则”或“修改规则”时发送的数据
# --------------------------------------------------------------------------
class UserPreferenceCreate(UserPreferenceBase):
    account_id: str = Field(..., description="该规则所属的系统账号 ID")


class UserPreferenceUpdate(BaseModel):
    """允许用户局部修改规则内容，通常是修改权重因子"""
    target_value: Optional[str] = None
    preference_factor: Optional[float] = Field(None, ge=0.0, le=10.0)


# --------------------------------------------------------------------------
# 3. 出站：响应标准 (Response Schema)
# 🛬 前端“偏好设置面板”列表渲染的数据源
# --------------------------------------------------------------------------
class UserPreferenceResponse(UserPreferenceBase):
    id: int = Field(..., description="规则的唯一主键 ID")
    account_id: str

    class Config:
        from_attributes = True