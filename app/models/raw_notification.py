from sqlalchemy import Column, Integer, String, Text, ForeignKey, UniqueConstraint, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class RawNotification(Base):
    __tablename__ = "raw_notifications"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey("fetch_accounts.id", ondelete="CASCADE"), nullable=False)
    account_msg_id = Column(String(255), nullable=False)
    sender = Column(String(255))
    subject = Column(String(255))
    content = Column(Text)
    cleaned_content = Column(Text, nullable=True)
    status = Column(String(50), default="pending")
    # [新增] 时间追踪字段
    received_at = Column(DateTime, nullable=True)  # 原始发件时间 (可能抓不到，允许为空)
    created_at = Column(DateTime, server_default=func.now())  # 入库时间 (自动填充)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())  # 更新时间 (自动更新)
    __table_args__ = (
        UniqueConstraint('account_id', 'account_msg_id', name='unique_account_msg'),
    )

    # 建立与账号表的正向关联 (多对一)
    account = relationship("FetchAccount", back_populates="notifications")

    # ==========================================
    # 【新增】建立与 AI 分析结果表的 1对1 正向关联
    # uselist=False : 确保一条生肉只对应一个打分结果
    # cascade : 确保如果这条生肉被删除了，它对应的 AI 打分也会自动销毁
    # ==========================================
    analysis = relationship(
        "NotificationAnalysis",
        back_populates="raw_notification",
        uselist=False,
        cascade="all, delete-orphan"
    )