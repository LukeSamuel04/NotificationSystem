# app/models/user_preference.py
from sqlalchemy import Column, String, Integer, Float, DateTime, func, Index
from app.db.base_class import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True, comment="主键ID")
    account_id = Column(String(255), nullable=False, index=True, comment="所属系统账号ID")
    platform = Column(String(50), nullable=False, comment="生效平台 (instagram, email, global)")
    preference_type = Column(String(50), nullable=False, comment="规则类型 (sender_id, topic, email_domain)")
    target_value = Column(String(255), nullable=False, comment="匹配目标值")

    # 💥 核心映射：乘积因子
    preference_factor = Column(Float, nullable=False, default=1.0, comment="偏好乘积因子")

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_rule_lookup", "account_id", "platform", "preference_type", "target_value"),
    )