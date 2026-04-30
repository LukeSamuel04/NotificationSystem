# app/schemas/notification.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    # --- 基础消息字段 (对应新的 Notification Model) ---
    id: int
    account_id: int
    account_msg_id: str
    sender: Optional[str] = None
    subject: Optional[str] = None
    cleaned_content: Optional[str] = None
    status: str

    # --- AI 分析字段 (通常通过关联查询从 NotificationAnalysis 获取) ---
    # 在 Service 层组装数据时，这些字段会被扁平化处理到这个 Response 中
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