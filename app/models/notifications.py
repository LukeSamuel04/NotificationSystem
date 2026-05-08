# app/models/notifications.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("fetch_accounts.id", ondelete="CASCADE"), nullable=False)

    #展示与统计用的冗余平台标识 (前端直接读取，免 JOIN 查询)
    platform = Column(String(50), nullable=False)

    account_msg_id = Column(String(255), nullable=False)
    sender = Column(String(255))

    #台侧发送者唯一 ID (用于后续的手动黑白名单、历史权重分配)
    external_sender_id = Column(String(255), nullable=True)

    subject = Column(String(255))

    #删除了生数据，只保留清洗后的 Markdown/纯文本
    cleaned_content = Column(Text, nullable=True)

    status = Column(String(50), default="pending")
    #是否是我主动发出的
    is_from_me = Column(Boolean, default=False, index=True)
    #记录被回复的消息 ID
    reply_to_mid = Column(String(255), nullable=True, index=True)
    #时间追踪字段
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    #唯一性约束（防止同一条消息被重复拉取/推送）
    __table_args__ = (
        UniqueConstraint('account_id', 'account_msg_id', name='uq_notifications_account_msg'),
    )

    # --- 关联关系映射 ---

    # 1. 账号关联 (多对一)
    account = relationship("FetchAccount", back_populates="notifications")

    # 2. AI 分析结果关联 (一对一)
    analysis = relationship(
        "NotificationAnalysis",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # 3. 冷数据载荷表关联 (一对一)
    payload = relationship(
        "NotificationPayload",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan"
    )