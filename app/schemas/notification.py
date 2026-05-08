# app/schemas/notification.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==========================================
# 1. 响应前端的 Schema (对应你的 Kanban 看板)
# ==========================================
class NotificationResponse(BaseModel):
    # --- 基础消息字段 (对应新的 Notification Model) ---
    id: int
    account_id: int

    # 💥 [新增] 平台标识，前端直接用它渲染 Instagram 或 Email 图标
    platform: str

    account_msg_id: str
    sender: Optional[str] = None

    # 💥 [新增] 发送者唯一 ID，用于前端展示或未来的手动黑名单逻辑
    external_sender_id: Optional[str] = None

    subject: Optional[str] = None
    cleaned_content: Optional[str] = None
    status: str

    # --- AI 分析字段 (通常通过关联查询从 NotificationAnalysis 获取) ---
    priority_score: Optional[float] = None
    category: Optional[str] = None
    summary: Optional[str] = None

    # --- 时间追踪字段 ---
    received_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        # 允许从 SQLAlchemy 模型对象直接创建 Schema 实例 (model_validate)
        from_attributes = True


# ==========================================
# 2. 💥 [新增] 接收 Meta Webhook 的专用 Schema
# ==========================================
# 💥 必须先定义被引用的类
class InstagramReplyTo(BaseModel):
    mid: str
class InstagramMessage(BaseModel):
    mid: str
    # 设为 Optional，因为有时候 Meta 会发来图片/被删除的消息而没有 text
    text: Optional[str] = ""
    is_echo: bool = False
    # 💥 新增：解析 Meta 载荷中的引用关系
    reply_to: Optional[InstagramReplyTo] = None


class InstagramSender(BaseModel):
    id: str
class InstagramRecipient(BaseModel):
    id: str

class InstagramMessagingEvent(BaseModel):
    sender: InstagramSender
    recipient: InstagramRecipient
    timestamp: int
    # 只有用户发消息时才有 message，如果是“已读回执”则没有，因此设为 Optional
    message: Optional[InstagramMessage] = None


class InstagramEntry(BaseModel):
    id: str  # 这个就是你要用来反向查表的 platform_account_id
    time: int
    messaging: List[InstagramMessagingEvent]


class InstagramWebhookPayload(BaseModel):
    object: str
    entry: List[InstagramEntry]