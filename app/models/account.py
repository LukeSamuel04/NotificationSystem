# app/models/account.py
from sqlalchemy import Column, Integer, String, Boolean, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class FetchAccount(Base):
    __tablename__ = "fetch_accounts"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    platform = Column(String(50), nullable=False)
    username = Column(String(100), nullable=False)  # 提拔为独立列，用于查重和展示
    config = Column(JSON, nullable=False)           # 存储底层的 user, password, host 等细节
    is_valid = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)

    notifications = relationship(
        "Notification",
        back_populates="account",
        cascade="all, delete-orphan"
    )