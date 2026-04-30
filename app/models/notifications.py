from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("fetch_accounts.id", ondelete="CASCADE"), nullable=False)
    account_msg_id = Column(String(255), nullable=False)
    sender = Column(String(255))
    subject = Column(String(255))

    # 💥 【核心变动】：删除了生数据，只保留清洗后的 Markdown/纯文本
    cleaned_content = Column(Text, nullable=True)

    status = Column(String(50), default="pending")

    # 时间追踪字段
    received_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 唯一性约束（防止同一条消息被重复拉取）
    __table_args__ = (
        UniqueConstraint('account_id', 'account_msg_id', name='uq_notifications_account_msg'),
    )

    # --- 关联关系映射 ---

    # 1. 账号关联 (多对一)
    account = relationship("FetchAccount", back_populates="notifications")

    # 2. AI 分析结果关联 (一对一)
    # 注意：你需要去 NotificationAnalysis 模型里，把原来的 back_populates="raw_notification" 改为 "notification"
    analysis = relationship(
        "NotificationAnalysis",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # 3. 💥 【新增】冷数据载荷表关联 (一对一)
    # 让你在代码里可以直接通过 notif.payload.raw_payload 拿到原始 JSON
    payload = relationship(
        "NotificationPayload",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan"
    )