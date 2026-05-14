# app/schemas/notification.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# 引入独立的子领域出站模具
from app.schemas.email_analysis import EmailAnalysisResponse
from app.schemas.im_session import IMSessionStateResponse


# --------------------------------------------------------------------------
# 1. 输出层：看板总览核心响应标准 (Response Schema)
# 💥 作为前端 Kanban 读取数据的唯一真理源，动态挂载不同渠道的 AI 分析熟肉
# --------------------------------------------------------------------------

class NotificationResponse(BaseModel):
    """
    通用生肉层与智慧插槽容器。
    无论底层是邮件还是 Instagram 消息，生肉基础字段保持绝对统一。
    AI 熟肉会根据 platform 自动填入对应的独立插槽中。
    """
    # --- 基础生肉追踪字段 ---
    id: int = Field(..., description="通知条目的自增主键 ID")
    account_id: int = Field(..., description="所属系统账号的整数 ID")
    platform: str = Field(..., description="渠道标识，前端借此区分渲染卡片类型 ('email' 或 'instagram')")
    account_msg_id: str = Field(..., description="第三方原始消息唯一 ID (如 Meta mid 或邮件 Message-ID)")
    status: str = Field(..., description="当前处理状态 (如：pending, processed, completed)")

    # --- 渠道差异化及上下文关联字段 ---
    sender: Optional[str] = Field(default=None, description="发件人显示名称")
    external_sender_id: Optional[str] = Field(default=None, description="外部发送方唯一标识 (IG User ID 或邮箱地址)")
    subject: Optional[str] = Field(default=None, description="消息主题 (仅邮件渠道存在，IM 默认置空)")
    cleaned_content: Optional[str] = Field(default=None, description="清洗脱敏后的正文纯文本内容")

    # --- 双向追踪特性 ---
    is_from_me: bool = Field(default=False, description="是否由系统主动发出的回复快照")
    reply_to_mid: Optional[str] = Field(default=None, description="回复的目标消息 ID，用于追踪对话线索")

    # --- 💥 核心架构升级：智慧层双插槽独立挂载 ---
    # 邮件专属插槽：仅当 platform == 'email' 时被 ORM 填充
    email_analysis: Optional[EmailAnalysisResponse] = Field(
        default=None,
        description="邮件专属 AI 分析产物挂载点"
    )

    # IM 专属插槽：仅当 platform == 'instagram' 时被填充
    # alias="im_session_state" 完美对接底层 SQLAlchemy 的 relationship 变量名映射
    im_analysis: Optional[IMSessionStateResponse] = Field(
        default=None,
        alias="im_session_state",
        description="即时通讯专属 AI 会话状态挂载点"
    )

    # --- 时间线记录 ---
    received_at: Optional[datetime] = Field(default=None, description="消息到达第三方平台的时间")
    created_at: Optional[datetime] = Field(default=None, description="系统捕获入库时间")
    updated_at: Optional[datetime] = Field(default=None, description="状态最后变更时间")

    class Config:
        from_attributes = True  # 允许无缝读取 SQLAlchemy ORM 模型对象
        populate_by_name = True  # 允许在序列化时识别并映射 alias 别名


# --------------------------------------------------------------------------
# 2. 输入层：看板卡片交互更新载荷 (Update Schema)
# 🛫 用于前端拖拽看板卡片改变所属栏目时触发的局部状态更新
# --------------------------------------------------------------------------

class NotificationUpdate(BaseModel):
    """前端看板操作发送的更新载荷"""
    status: str = Field(..., description="目标变动状态 (如前端拖拽至 '已处理' 栏触发更新)")


# --------------------------------------------------------------------------
# 3. 输入层：Meta Webhook 入站拦截载荷 (Webhook Input Schemas)
# 🛡️ 严防死守外部输入流，自动将 Meta 原生复杂嵌套转为 Python 安全对象
# --------------------------------------------------------------------------

class InstagramReplyTo(BaseModel):
    mid: str


class InstagramMessage(BaseModel):
    mid: str
    text: Optional[str] = ""
    is_echo: bool = False
    reply_to: Optional[InstagramReplyTo] = None


class InstagramSender(BaseModel):
    id: str


class InstagramRecipient(BaseModel):
    id: str


class InstagramMessagingEvent(BaseModel):
    sender: InstagramSender
    recipient: InstagramRecipient
    timestamp: int
    message: Optional[InstagramMessage] = None


class InstagramEntry(BaseModel):
    id: str
    time: int
    messaging: List[InstagramMessagingEvent]


class InstagramWebhookPayload(BaseModel):
    """接收 Meta Graph API 推送的顶层 Webhook 结构报文"""
    object: str
    entry: List[InstagramEntry]