# app/services/context/manager.py (顶层调度器)
from sqlalchemy.orm import Session
from app.models.notifications import Notification
from .im.manager import get_im_formatted_context  # 💥 引入 IM 小总管
#from .email.manager import get_email_formatted_context


async def get_formatted_context(db: Session, notification: Notification) -> str:
    platform = notification.platform.lower()

    if platform == "instagram":
        # 转发给 IM 模块处理
        return await get_im_formatted_context(db, notification)

    elif platform == "email":
        # 转发给 Email 模块处理 (待实现)
        return f"Email 内容: {notification.cleaned_content}"

    return notification.cleaned_content