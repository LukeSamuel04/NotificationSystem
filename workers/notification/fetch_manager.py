import logging
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.notifications import Notification
from app.models.notification_payloads import NotificationPayload
from app.models.account import FetchAccount
from ..notification.utils.html_cleaner import clean_html

# 引入极速异步邮件引擎
from workers.notification.fetchers.email_fetcher import EmailFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("FetchManager")


def process_and_save_message(db: Session, account: FetchAccount, raw_message_data: dict):
    """
    处理单条抓取到的原始消息并存入数据库 (保持同步逻辑，由外部线程池驱动)
    """
    try:
        existing = db.query(Notification).filter(
            Notification.account_id == account.id,
            Notification.account_msg_id == raw_message_data['account_msg_id']
        ).first()

        if existing:
            return None

        platform = account.platform.lower()
        raw_content = raw_message_data.get('content', '')
        cleaned_text = clean_html(raw_content) if platform == 'email' else raw_content

        new_notification = Notification(
            account_id=account.id,
            account_msg_id=raw_message_data['account_msg_id'],
            sender=raw_message_data['sender'],
            subject=raw_message_data['subject'],
            cleaned_content=cleaned_text,
            status="pending",
            received_at=raw_message_data.get('received_at')
        )
        db.add(new_notification)
        db.flush()

        save_backup_data = raw_message_data.copy()
        if isinstance(save_backup_data.get('received_at'), datetime):
            save_backup_data['received_at'] = save_backup_data['received_at'].isoformat()

        payload_record = NotificationPayload(
            notification_id=new_notification.id,
            raw_payload={
                "source_platform": platform,
                "raw_ingested_content": raw_content,
                "ingestion_metadata": {"worker_version": "2.1", "original_data": save_backup_data}
            }
        )
        db.add(payload_record)
        db.commit()
        return new_notification
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 消息入库失败: {str(e)}")
        return None


async def fetch_messages_for_account(account: FetchAccount) -> list[dict]:
    """分类处理标记已读 (纯异步函数)"""
    platform = account.platform.lower()
    if platform == 'email':
        account_config = getattr(account, 'config', {}) or {}
        config = {
            "host": account_config.get("host"),
            "user": account.username,
            "password": account.password  # 确保使用最新的 account 属性
        }
        try:
            fetcher = EmailFetcher(config)
            raw_msgs = await fetcher.fetch_new()

            # 批量标记已读，减少网络 IO 往返
            await asyncio.gather(*[fetcher.mark_as_processed(msg["msg_id"]) for msg in raw_msgs])

            return [{
                "account_msg_id": msg["msg_id"],
                "sender": msg.get("sender", "Unknown"),
                "subject": msg.get("subject", "No Subject"),
                "content": msg.get("content", ""),
                "received_at": datetime.now()
            } for msg in raw_msgs]
        except Exception as e:
            logger.error(f"❌ 邮件抓取失败: {e}")
            return []
    return []


async def fetch_loop(stop_event: asyncio.Event, new_data_event: asyncio.Event, poll_interval: int = 60):
    """
    抓取引擎主循环：已接入 stop_event 遥控器与线程隔离技术
    """
    logger.info("🚀 抓取引擎 (Fetch Loop) 已就绪...")

    while not stop_event.is_set():
        has_new_data = False
        db: Session = SessionLocal()
        try:
            active_accounts = db.query(FetchAccount).filter(
                FetchAccount.is_active == True,
                FetchAccount.is_valid == True
            ).all()

            for account in active_accounts:
                raw_messages = await fetch_messages_for_account(account)

                # 💥 核心改进：将同步入库逻辑丢进线程池，防止阻塞 API 主线程
                for raw_msg in raw_messages:
                    result = await asyncio.to_thread(process_and_save_message, db, account, raw_msg)
                    if result:
                        has_new_data = True

        except Exception as e:
            logger.error(f"💥 抓取循环发生错误: {str(e)}")
        finally:
            db.close()

        if has_new_data:
            new_data_event.set()

        # 使用优雅休眠，随时响应停机信号
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass

    logger.info("🛑 抓取引擎已安全下线。")