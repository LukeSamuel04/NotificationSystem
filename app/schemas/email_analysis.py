# app/schemas/email_analysis.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

# --------------------------------------------------------------------------
# 1. 基础智慧基因 (Base Schema)
# 💥 这里定义了 AI 分析产物的核心字段，作为后续“入站”和“出站”模型的基类
# --------------------------------------------------------------------------

class EmailAnalysisBase(BaseModel):
    """
    AI 邮件分析结果的共性字段。
    无论是刚从 AI 吐出来的，还是从数据库查出来的，都必须具备这些核心属性。
    """
    priority_score: int = Field(..., ge=1, le=10, description="AI 评定的紧急程度评分 (1-10)")
    category_id: int = Field(..., description="关联的分类 ID (如：1-技术, 2-财务)")
    summary: str = Field(..., description="AI 生成的邮件内容精炼摘要")


# --------------------------------------------------------------------------
# 2. 入站写入模具 (Create Schema)
# 🛫 用于后端接收 AI 处理结果并准备写入数据库的阶段
# --------------------------------------------------------------------------

class EmailAnalysisCreate(EmailAnalysisBase):
    """
    创建分析记录时的载荷。
    在 Base 的基础上增加了 notification_id，用于将其死死绑定到具体的某封邮件上。
    """
    notification_id: int = Field(..., description="所属通知条目的数据库 ID")


# --------------------------------------------------------------------------
# 3. 出站响应标准 (Response Schema)
# 🛬 完美对齐工业级命名规范：用于从数据库读取并返回给前端看板
# --------------------------------------------------------------------------

class EmailAnalysisResponse(EmailAnalysisBase):
    """
    回显给前端看板的完整模型。
    包含所有数据库生成的物理字段，作为 NotificationResponse 的“子插件”挂载。
    """
    id: int = Field(..., description="分析记录的唯一主键 ID")
    notification_id: int = Field(..., description="关联的通知 ID")
    created_at: datetime = Field(..., description="分析任务完成的时间戳")

    class Config:
        # 允许 Pydantic 直接读取 SQLAlchemy 模型对象 (ORM 兼容模式)
        from_attributes = True