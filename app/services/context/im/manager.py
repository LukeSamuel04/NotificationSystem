# app/services/context/im/manager.py
import logging
from sqlalchemy.orm import Session
from app.models.notifications import Notification

# 💥 引入同目录下的 IM 专用组件
from .context_finder import get_im_context
from .formatter import format_notification_context

logger = logging.getLogger(__name__)


async def get_im_formatted_context(db: Session, notification: Notification) -> str:
    """
    IM 模块内部管理器：
    专门负责串联 IM 的检索逻辑与文本格式化逻辑。
    """
    try:
        # 1. 运行双层跳跃检索算法
        context_list = await get_im_context(db, notification)

        # 2. 转化为带角色和精准时间定位的剧本
        return format_notification_context(context_list)

    except Exception as e:
        logger.error(f"❌ IM 上下文处理失败: {e}")
        # 发生异常时，至少返回当前消息内容作为兜底
        return f"【消息内容】: {notification.cleaned_content}"