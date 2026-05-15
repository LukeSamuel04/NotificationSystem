# app/schemas/notification.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.email_analysis import EmailAnalysisResponse
from app.schemas.im_session import IMSessionStateResponse


# --------------------------------------------------------------------------
# [新增] 0. 冷表快照标准 (Analysis Payload)
# 🔍 为前端的“可解释性透镜 (Explainability Lens)”提供因子拆解数据
# --------------------------------------------------------------------------
class AnalysisPayloadResponse(BaseModel):
    id: int
    analysis_data: Dict[str, Any] = Field(..., description="包含泊松因子、偏好因子等计算快照的 JSON")
    user_feedback_score: Optional[int] = Field(default=None, description="用户的人工修正反馈分")

    class Config:
        from_attributes = True


# --------------------------------------------------------------------------
# 1. 输出层：看板总览核心响应标准 (Response Schema)
# --------------------------------------------------------------------------
class NotificationResponse(BaseModel):
    id: int = Field(..., description="通知条目的自增主键 ID")
    account_id: int = Field(..., description="所属系统账号的 ID")
    platform: str = Field(..., description="渠道标识 ('email' 或 'instagram')")
    account_msg_id: str = Field(..., description="第三方原始消息唯一 ID")
    status: str = Field(..., description="当前处理状态")
    # 💥 核心修复：把下面这行补上，让后端把已读状态放行给前端
    is_read: bool = Field(default=False, description="是否已读")
    sender: Optional[str] = None
    external_sender_id: Optional[str] = None
    subject: Optional[str] = None
    cleaned_content: Optional[str] = None

    is_from_me: bool = False
    reply_to_mid: Optional[str] = None

    # --- 💥 核心架构升级：智慧层三插槽独立挂载 ---
    email_analysis: Optional[EmailAnalysisResponse] = Field(default=None)

    im_analysis: Optional[IMSessionStateResponse] = Field(
        default=None,
        alias="im_session_state"
    )

    # 💥 新增：冷数据快照插槽，供给前端解析公式
    analysis_payload: Optional[AnalysisPayloadResponse] = Field(default=None)

    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
        populate_by_name = True


# --------------------------------------------------------------------------
# 2. 输入层：看板卡片交互更新载荷 (Update Schema)
# --------------------------------------------------------------------------
class NotificationUpdate(BaseModel):
    """前端拖拽看板卡片改变状态"""
    status: Optional[str] = None
    # 💥 核心修复：补充 is_read 字段，允许前端修改已读/未读状态
    is_read: Optional[bool] = None


class FeedbackUpdate(BaseModel):
    """💥 新增：用户在前端点赞/踩，修正 AI 打分的反馈载荷"""
    user_feedback_score: int = Field(..., ge=1, le=10)


# (下面的 Instagram Webhook 相关 Schema 保持原样，无需修改)
class InstagramReplyTo(BaseModel):
    mid: str


class InstagramMessage(BaseModel):
    mid: str
    text: Optional[str] = ""
    is_echo: bool = False
    reply_to: Optional[InstagramReplyTo] = None


class InstagramSender(BaseModel):
    id: str


class InstagramRecipient(BaseModel):
    id: str


class InstagramMessagingEvent(BaseModel):
    sender: InstagramSender
    recipient: InstagramRecipient
    timestamp: int
    message: Optional[InstagramMessage] = None


class InstagramEntry(BaseModel):
    id: str
    time: int
    messaging: List[InstagramMessagingEvent]


class InstagramWebhookPayload(BaseModel):
    object: str
    entry: List[InstagramEntry]