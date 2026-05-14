# app/models/analysis_payload.py
from sqlalchemy import Column, String, Integer, JSON, DateTime, func, ForeignKey
from app.db.base_class import Base


class AnalysisPayload(Base):
    __tablename__ = "analysis_payloads"

    id = Column(Integer, primary_key=True, index=True)
    notification_id = Column(Integer, nullable=False, index=True, comment="关联的原始消息ID")
    account_id = Column(String(255), nullable=False, index=True)
    platform = Column(String(50), nullable=False)

    # 存储所有的中间因子
    analysis_data = Column(JSON, nullable=False)

    # 用于存储用户回馈的 Ground Truth
    user_feedback_score = Column(Integer, nullable=True, comment="用户反馈的分数 (1-10)")

    created_at = Column(DateTime, server_default=func.now())