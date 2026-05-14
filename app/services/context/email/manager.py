# app/services/context/email/manager.py
import logging
from sqlalchemy.orm import Session
from app.models.notifications import Notification

# 💥 引入同目录下的 Email 专用组件
from .context_finder import EmailContextFinder
from .formatter import EmailFormatter

logger = logging.getLogger(__name__)


async def get_email_formatted_context(db: Session, notification: Notification) -> str:
    """
    Email 模块内部管理器：
    负责串联 Email 的无状态检索逻辑与文本提纯格式化逻辑。
    对外保持与 IM 模块相同的调用签名 (Signature)。
    """
    try:
        # 1. 运行 Email 专用的无状态广度/深度检索算法，捞出并排好序的历史记录
        # 注意：这里的 ContextFinder 是同步查询，直接调用即可
        context_list = EmailContextFinder.get_context_records(db, notification)

        # 2. 转化为分离了【对话背景】和【当前最新诉求】的纯净剧本
        return EmailFormatter.format_email_script(context_list)

    except Exception as e:
        logger.error(f"❌ Email 上下文处理失败: {e}")
        # 发生异常时，至少返回当前消息内容作为兜底，保证 AI 算分流水线不中断
        return f"【最新邮件诉求】:\n{notification.cleaned_content}"