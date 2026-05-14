# app/schemas/im_session.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ==========================================
# 1. AI 侧 Schema：用于严格约束大模型的结构化输出
# ==========================================
class IMSessionAIResult(BaseModel):
    """
    接收 AI 结构化输出的基类模型。
    大模型需要严格按照这里的字段名和类型返回 JSON。
    (注意：AI 不需要返回 account_id，因为它不关心这个对话是发给哪个系统账号的)
    """
    current_topic: str = Field(..., description="提取出的当前核心诉求/话题")
    priority_score: int = Field(..., ge=1, le=10, description="紧急度评分 1-10，10为最紧急")
    summary_snapshot: str = Field(..., description="对话上下文的浓缩摘要，尽量简短精炼")

# ==========================================
# 2. 数据库更新侧 Schema (可选)
# ==========================================
class IMSessionUpdate(IMSessionAIResult):
    """
    用于更新数据库记录的 Schema
    继承了 AI 的结果，并加上了需要我们自己手动更新的时间戳
    """
    last_message_at: Optional[datetime] = None

# ==========================================
# 3. 前端/响应侧 Schema：用于 API 返回给你的看板页面
# ==========================================
class IMSessionStateResponse(IMSessionAIResult):
    """
    给前端看板展示用的完整模型。
    包含了所有数据库字段。
    """
    external_sender_id: str
    account_id: int
    platform: str
    last_message_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        # FastAPI 专属配置：允许直接将 SQLAlchemy 的 ORM 对象转化为这个 Pydantic 模型
        from_attributes = True