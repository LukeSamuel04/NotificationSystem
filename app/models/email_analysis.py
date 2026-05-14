# app/models/email_analysis.py
from sqlalchemy import Column, Integer, Text, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class EmailAnalysis(Base):
    # 💥 表名更改为 email_analysis
    __tablename__ = "email_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 核心外键：依然指向生肉表 (锚定的是这组 Email Thread 里最新的一封邮件)
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)

    # 强类型 AI 算分结果
    priority_score = Column(Integer, default=0)
    category_id = Column(Integer, index=True)
    summary = Column(Text)

    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint('notification_id', name='unique_email_notification'),
    )

    # 反向关联
    notification = relationship("Notification", back_populates="email_analysis")