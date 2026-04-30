from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base_class import Base


class NotificationAnalysis(Base):
    __tablename__ = "notification_analysis"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    # 核心外键：指向生肉表
    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"), nullable=False)

    # AI 算分结果字段
    priority_score = Column(Float, default=0.0)
    category = Column(String(255))
    summary = Column(Text)
    created_at = Column(DateTime, server_default=func.now())

    # 声明你在 Navicat 里建的唯一索引
    __table_args__ = (
        UniqueConstraint('notification_id', name='unique_notification'),
    )

    # 建立与信息表的反向关联
    notification = relationship("Notification", back_populates="analysis")