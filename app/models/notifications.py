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
    status = Column(String, default="pending", index=True)
    is_read = Column(Boolean, default=False, index=True)
    #status = Column(String(50), default="pending")
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

    # 2. 💥 核心修复：更新为 email_analysis 映射，完美对接底层 back_populates
    email_analysis = relationship(
        "EmailAnalysis",  # 对应 EmailAnalysis 类的名字
        back_populates="notification",
        uselist=False,  # 一对一关系
        cascade="all, delete-orphan",
    )

    # 3. 冷数据载荷表关联 (一对一)
    payload = relationship(
        "NotificationPayload",
        back_populates="notification",
        uselist=False,
        cascade="all, delete-orphan"
    )

    # 4. 💥 核心修复：IM Session 虚拟关联映射
    # 由于 IM 会话是由两个字段联合确认的，且没有物理外键约束，这里使用 primaryjoin 手动寻址
    im_session_state = relationship(
        "IMSessionState",
        primaryjoin="and_(Notification.account_id == foreign(IMSessionState.account_id), Notification.external_sender_id == foreign(IMSessionState.external_sender_id))",
        uselist=False,
        viewonly=True  # 设为只读，避免在这个模型里意外修改 IM 的独立状态
    )