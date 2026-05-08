# app/services/instagram/webhook_manager.py
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models.account import FetchAccount
from app.models.notifications import Notification
from app.schemas.notification import InstagramWebhookPayload

logger = logging.getLogger(__name__)


async def process_instagram_webhook(
        db: Session,
        payload: InstagramWebhookPayload,
        is_from_me: bool = False
):
    """
    全量重构版：修正 external_sender_id 逻辑，确保存储的是“对话伙伴”的 ID
    """
    # 1. 过滤空数据
    if not payload.entry or not payload.entry[0].messaging:
        return

    meta_id = payload.entry[0].id  # 商业号本身的平台 ID
    messaging_event = payload.entry[0].messaging[0]

    # 2. 过滤非文字消息
    if not messaging_event.message or not messaging_event.message.text:
        return

    message_data = messaging_event.message
    sender_id = messaging_event.sender.id      # 发送者 ID
    recipient_id = messaging_event.recipient.id  # 接收者 ID
    raw_text = message_data.text
    msg_id = message_data.mid

    # 💥 核心修正逻辑：确定“对话伙伴”的 ID
    # 无论谁发的消息，我们要记录的是这封信“跟谁聊”
    if is_from_me:
        # 如果是我发的（Echo），那么对方是接收者
        chat_partner_id = recipient_id
    else:
        # 如果是对方发的，对方就是发送者
        chat_partner_id = sender_id

    # 3. 提取引用 ID
    reply_to_mid = None
    if message_data.reply_to:
        reply_to_mid = message_data.reply_to.mid

    # 4. 转换原始发送时间戳
    received_time = datetime.fromtimestamp(messaging_event.timestamp / 1000.0)

    try:
        # 5. 寻找归属账号
        target_account = db.query(FetchAccount).filter(
            FetchAccount.platform_account_id == meta_id,
            FetchAccount.platform == "instagram"
        ).first()

        if not target_account:
            logger.warning(f"⚠️ 未绑定的 Meta ID: {meta_id}，消息已丢弃。")
            return

        # 6. 写入数据库
        new_notification = Notification(
            account_id=target_account.id,
            platform="instagram",
            account_msg_id=msg_id,
            # 这里的 sender 只是给人看的标签
            sender="Me" if is_from_me else "IG User",
            # 💥 关键点：external_sender_id 永远存客户 ID，方便后续根据此 ID 聚合上下文
            external_sender_id=chat_partner_id,
            cleaned_content=raw_text,
            is_from_me=is_from_me,
            reply_to_mid=reply_to_mid,
            received_at=received_time,
            status="pending"
        )

        db.add(new_notification)
        db.commit()

        status_label = "我方回声" if is_from_me else "对方来信"
        logger.info(f"✅ [{status_label}] 消息入库成功 (Partner: {chat_partner_id})")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 消息入库失败: {e}")