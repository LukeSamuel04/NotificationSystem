import logging
import time
import asyncio
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.notifications import Notification
from app.models.notification_payloads import NotificationPayload
from app.models.account import FetchAccount
from app.services.html.html_cleaner import clean_html

# 引入你的极速异步邮件引擎
from workers.fetchers.email_fetcher import EmailFetcher

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def process_and_save_message(db: Session, account: FetchAccount, raw_message_data: dict):
    """处理单条抓取到的原始消息并存入数据库"""
    try:
        # 1. 幂等性检查
        existing = db.query(Notification).filter(
            Notification.account_id == account.id,
            Notification.account_msg_id == raw_message_data['account_msg_id']
        ).first()

        if existing:
            # 💥 新增：重复消息的控制台提示
            logger.warning(
                f"⏩ 跳过重复消息: [ID {raw_message_data['account_msg_id']}] {raw_message_data['subject'][:20]}...")
            return None

        # 2. 内容清洗
        platform = account.platform.lower()
        raw_content = raw_message_data.get('content', '')
        cleaned_text = clean_html(raw_content) if platform == 'email' else raw_content

        # 3. 创建主表记录
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

        # 4. 处理 JSON 时间序列化
        save_backup_data = raw_message_data.copy()
        if isinstance(save_backup_data.get('received_at'), datetime):
            save_backup_data['received_at'] = save_backup_data['received_at'].isoformat()

        # 5. 创建副表记录
        raw_payload_json = {
            "source_platform": platform,
            "raw_ingested_content": raw_content,
            "ingestion_metadata": {
                "worker_version": "2.0",
                "original_data": save_backup_data
            }
        }

        payload_record = NotificationPayload(
            notification_id=new_notification.id,
            raw_payload=raw_payload_json
        )
        db.add(payload_record)

        # 6. 最终提交入库
        db.commit()
        logger.info(f"✅ 成功入库: [{platform.upper()}] ID: {new_notification.id} | {new_notification.subject[:20]}...")
        return new_notification

    except Exception as e:
        db.rollback()
        # 💥 新增：入库失败的详细报错
        logger.error(f"❌ 入库失败: [消息ID {raw_message_data['account_msg_id']}] 错误信息: {str(e)}")
        # 这里不抛出异常，让主循环继续处理下一封邮件
        return None


def fetch_messages_for_account(account: FetchAccount) -> list[dict]:
    """根据不同平台路由并处理标记已读"""
    platform = account.platform.lower()

    if platform == 'email':
        account_config = getattr(account, 'config', {}) or {}
        host = account_config.get("host")
        password = account_config.get("password")

        if not host or not password:
            logger.error(f"❌ 账号 {account.username} 配置不完整。")
            return []

        config = {"host": host, "user": account.username, "password": password}

        try:
            # 💥 封装异步任务包：抓取 + 标记已读
            async def run_fetch_cycle():
                fetcher = EmailFetcher(config)
                raw_msgs = await fetcher.fetch_new()

                # 抓取到之后，立刻在服务器上标记为已读，防止下次重复抓取
                for msg in raw_msgs:
                    await fetcher.mark_as_processed(msg["msg_id"])

                return raw_msgs

            # 执行异步链
            raw_messages = asyncio.run(run_fetch_cycle())

            formatted_messages = []
            for msg in raw_messages:
                formatted_messages.append({
                    "account_msg_id": msg["msg_id"],
                    "sender": msg.get("sender", "Unknown"),
                    "subject": msg.get("subject", "No Subject"),
                    "content": msg.get("content", ""),
                    "received_at": datetime.now()
                })
            return formatted_messages

        except Exception as e:
            logger.error(f"❌ 邮件引擎执行失败: {e}")
            return []

    elif platform in ['instagram', 'whatsapp']:
        logger.info(f"🚧 平台 [{platform.upper()}] 暂未接入。")
        return []

    return []


def worker_loop(poll_interval: int = 60):
    """Manager Worker 轮询主循环"""
    logger.info("🚀 抓取 Manager Worker 已启动...")

    while True:
        logger.info(f"--- 🔍 开始抓取巡视 ---")
        db: Session = SessionLocal()
        try:
            active_accounts = db.query(FetchAccount).filter(FetchAccount.is_active == True).all()

            for account in active_accounts:
                logger.info(f"📡 正在拉取账号: {account.username}...")
                raw_messages = fetch_messages_for_account(account)

                if raw_messages:
                    logger.info(f"📥 准备处理 {len(raw_messages)} 条数据...")
                    for raw_msg in raw_messages:
                        process_and_save_message(db, account, raw_msg)
                else:
                    logger.info(f"📭 账号 {account.username} 暂无新消息。")

        except Exception as e:
            logger.error(f"💥 循环发生严重错误: {str(e)}")
        finally:
            db.close()

        logger.info(f"💤 休眠 {poll_interval} 秒...\n")
        time.sleep(poll_interval)


if __name__ == "__main__":
    try:
        worker_loop(poll_interval=60)
    except KeyboardInterrupt:
        logger.info("\n🛑 Worker 已安全停止。")