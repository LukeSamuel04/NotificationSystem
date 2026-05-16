# workers/notification/fetch_manager.py
#监测新邮件、例行扫盘，把新消息送进数据引擎
import logging
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.notifications import Notification
from app.models.notification_payloads import NotificationPayload
from app.models.account import FetchAccount
from ..notification.utils.html_cleaner import clean_html

from workers.notification.fetchers.email_fetcher import EmailFetcher
from workers.ai.managers.email_scheduler import trigger_email_scan

logger = logging.getLogger("FetchManager")

def process_and_save_message(db: Session, account: FetchAccount, raw_message_data: dict):
    """处理单条消息并提交进数据库引擎"""
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

        is_from_me = raw_message_data.get('is_from_me', False)
        final_status = "processed" if is_from_me else "pending"

        new_notification = Notification(
            account_id=account.id,
            platform=platform,
            account_msg_id=raw_message_data['account_msg_id'],
            sender=raw_message_data['sender'],
            external_sender_id=raw_message_data.get('external_sender_id'),
            reply_to_mid=raw_message_data.get('reply_to_mid'),
            subject=raw_message_data['subject'],
            cleaned_content=cleaned_text,
            status=final_status,
            is_from_me=is_from_me,
            received_at=raw_message_data.get('received_at', datetime.now())
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
                "ingestion_metadata": {"original_data": save_backup_data}
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
    """协同调用底层网关完成数据采集与回写"""
    platform = account.platform.lower()
    if platform == 'email':
        account_config = getattr(account, 'config', {}) or {}
        config = {
            "host": account_config.get("host"),
            "user": account.username,
            "password": account_config.get("password")
        }
        try:
            fetcher = EmailFetcher(config)
            raw_msgs = await fetcher.fetch_new()

            # 筛选出需要标记已读的目标（第三方寄送的信件）
            msgs_to_mark = [msg for msg in raw_msgs if not msg.get("is_from_me")]
            if msgs_to_mark:
                # 💥 防御性打磨：稍微给云端1秒喘息期，保障并发套接字连接稳定性
                await asyncio.sleep(1)
                await asyncio.gather(*[
                    fetcher.mark_as_processed(
                        msg["account_msg_id"],
                        # 完美提取底层写入的原生出处目录，规避盲目检索
                        folder=msg.get("source_folder", "INBOX")
                    ) for msg in msgs_to_mark
                ])

            return [{
                "account_msg_id": msg["account_msg_id"],
                "reply_to_mid": msg.get("reply_to_mid"),
                "sender": msg.get("sender", "Unknown"),
                "external_sender_id": msg.get("external_sender_id"),
                "subject": msg.get("subject", "No Subject"),
                "content": msg.get("content", ""),
                "is_from_me": msg.get("is_from_me", False),
                "received_at": datetime.now()
            } for msg in raw_msgs]
        except Exception as e:
            logger.error(f"❌ 邮件协议协同断开: {e}")
            return []
    return []

async def fetch_loop(stop_event: asyncio.Event, new_data_event: asyncio.Event, poll_interval: int = 60):
    """常驻级静默扫盘死循环引擎"""
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
                for raw_msg in raw_messages:
                    result = await asyncio.to_thread(process_and_save_message, db, account, raw_msg)
                    if result:
                        has_new_data = True

        except Exception as e:
            logger.error(f"💥 抓取循环发生错误: {str(e)}")
        finally:
            db.close()

        if has_new_data:
            logger.info("⚡ 侦测到新邮件入库，正在直接唤醒 AI 算分执行器...")
            new_data_event.set()
            trigger_email_scan()

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=poll_interval)
        except asyncio.TimeoutError:
            pass

    logger.info("🛑 抓取引擎已安全下线。")