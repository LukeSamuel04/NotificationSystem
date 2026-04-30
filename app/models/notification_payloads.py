from sqlalchemy import Column, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class NotificationPayload(Base):
    __tablename__ = "notification_payloads"

    # 主键，同时作为指向主表的外键
    notification_id = Column(
        Integer,
        ForeignKey("notifications.id", ondelete="CASCADE"),
        primary_key=True
    )

    # 💥 【终极黑盒】：统一以 JSON 格式存储所有平台的原始载荷和元数据
    raw_payload = Column(JSON, nullable=False)

    # 建立与主表的反向关联
    notification = relationship("Notification", back_populates="payload")