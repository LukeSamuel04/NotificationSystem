# app/models/im_session.py
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, func
from app.db.base_class import Base


class IMSessionState(Base):
    __tablename__ = "im_session_states"

    # 联合主键
    external_sender_id = Column(String(255), primary_key=True, index=True, comment="外部联系人 ID")
    account_id = Column(String(255), primary_key=True, index=True, comment="系统接收账号 ID")

    platform = Column(String(50), index=True, comment="所属平台 (如 instagram)")
    current_topic = Column(String(255), comment="当前核心诉求/话题")
    priority_score = Column(Integer, comment="紧急度评分 1-10")
    summary_snapshot = Column(Text, comment="对话上下文浓缩摘要")
    last_message_at = Column(DateTime, comment="该会话最后一次互动的实际时间")

    # 💥 保留：泊松分布期望值基线 (当前观察短窗内的 k 值将通过动态聚合查询获得)
    historical_lambda = Column(Float, default=0.0, comment="历史基线：该联系人平均每小时发送的消息数")

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())