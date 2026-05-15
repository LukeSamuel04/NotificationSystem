# app/schemas/notification.py
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.schemas.email_analysis import EmailAnalysisResponse
from app.schemas.im_session import IMSessionStateResponse


class AnalysisPayloadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    analysis_data: Dict[str, Any]
    user_feedback_score: Optional[int] = None


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    platform: str
    account_msg_id: str
    status: str
    is_read: bool = False
    sender: Optional[str] = None
    external_sender_id: Optional[str] = None
    subject: Optional[str] = None
    cleaned_content: Optional[str] = None
    is_from_me: bool = False
    reply_to_mid: Optional[str] = None

    email_analysis: Optional[EmailAnalysisResponse] = None
    im_session_state: Optional[IMSessionStateResponse] = None

    # 💥 完美映射：直接使用底层暴露的 analysis_payload，100% 对齐你的前端 TS 接口！
    analysis_payload: Optional[AnalysisPayloadResponse] = None

    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class NotificationUpdate(BaseModel):
    status: Optional[str] = None
    is_read: Optional[bool] = None


class FeedbackUpdate(BaseModel):
    user_feedback_score: int = Field(..., ge=1, le=10)


# ================= Webhook 相关 =================
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