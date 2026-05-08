# app/models/account.py
from sqlalchemy import Column, Integer, String, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class FetchAccount(Base):
    __tablename__ = "fetch_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    #平台侧唯一标识 (如 Instagram Business ID, Email 地址)
    platform_account_id = Column(String(255), nullable=False)

    platform = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)  # 提拔为独立列，用于查重和展示
    config = Column(JSON, nullable=False)  # 存储底层的 user, password, host 等细节
    is_valid = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    # 复合唯一约束：确保 "平台 + 外部ID" 绝对唯一
    __table_args__ = (
        UniqueConstraint('platform', 'platform_account_id', name='uk_platform_account_id'),
    )

    notifications = relationship(
        "Notification",
        back_populates="account",
        cascade="all, delete-orphan"
    )