# app/models/notifications.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("fetch_accounts.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(50), nullable=False)
    account_msg_id = Column(String(255), nullable=False)
    sender = Column(String(255))
    external_sender_id = Column(String(255), nullable=True)
    subject = Column(String(255))
    cleaned_content = Column(Text, nullable=True)
    status = Column(String, default="pending", index=True)
    is_read = Column(Boolean, default=False, index=True)
    is_from_me = Column(Boolean, default=False, index=True)
    reply_to_mid = Column(String(255), nullable=True, index=True)
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint('account_id', 'account_msg_id', name='uq_notifications_account_msg'),
    )

    account = relationship("FetchAccount", back_populates="notifications")

    email_analysis = relationship(
        "EmailAnalysis",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # 保持原有的原始载荷映射不变，保护其他底层拉取逻辑
    payload = relationship(
        "NotificationPayload",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # 💥 核心修复：移除 back_populates，使用 primaryjoin 手动指定 JOIN 条件，彻底绕过无外键报错！
    analysis_payload = relationship(
        "AnalysisPayload",
        primaryjoin="Notification.id == foreign(AnalysisPayload.notification_id)",
        uselist=False,
        cascade="all, delete-orphan"
    )

    im_session_state = relationship(
        "IMSessionState",
        primaryjoin="and_(Notification.account_id == foreign(IMSessionState.account_id), Notification.external_sender_id == foreign(IMSessionState.external_sender_id))",
        uselist=False,
        viewonly=True
    )