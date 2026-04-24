from sqlalchemy import Column, Integer, String, Text, DateTime, Float
from datetime import datetime
from app.db.base_class import Base  # 导入基类


class Notification(Base):
    # 核心：必须和你在 Navicat 里的表名完全一致
    __tablename__ = "email"

    # 1. 基础字段
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sender = Column(String(255), nullable=False)
    subject = Column(String(255))

    # 2. 内容字段（Text 对应你的 longtext）
    raw_content = Column(Text)
    processed_content = Column(Text)

    # 3. AI 分析字段
    priority_score = Column(Float, default=0.0)
    category = Column(String(255))
    status = Column(String(20), default="pending")

    # 4. 时间字段
    received_at = Column(DateTime)
    # 这里的 datetime.now 是 Python 层面的默认值
    created_at = Column(DateTime, default=datetime.now)

    # 方便调试：打印这个对象时显示它的标题
    def __repr__(self):
        return f"<Notification(id={self.id}, subject='{self.subject}')>"