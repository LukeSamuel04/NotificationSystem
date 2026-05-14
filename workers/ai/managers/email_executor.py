# workers/ai/managers/email_executor.py
import logging
from sqlalchemy.orm import Session

# 导入底层数据模型
from app.models.notifications import Notification
from app.models.account import FetchAccount
from app.models.email_analysis import EmailAnalysis

# 导入上下文服务与算分模型
from app.services.context.email.manager import get_email_formatted_context
from workers.ai.models.email.scorer import analyze_email_context
from app.services.local_scoring.priority_orchestrator import PriorityOrchestrator

logger = logging.getLogger("EmailExecutor")


async def process_pending_emails(db: Session) -> int:
    pending_threads = db.query(
        Notification.subject,
        Notification.account_id
    ).filter(
        Notification.status == "pending",
        Notification.platform == "email"
    ).distinct().all()

    if not pending_threads:
        return 0

    orchestrator = PriorityOrchestrator(db)
    processed_threads_count = 0

    for subject, raw_account_id in pending_threads:
        try:
            # 💥 运行时防御装甲同步加固
            account_id = str(raw_account_id)

            valid_account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
            if not valid_account:
                continue

            clean_subject = subject or "无主题"

            latest_msg = db.query(Notification).filter(
                Notification.subject == subject,
                Notification.account_id == account_id,
                Notification.status == "pending",
                Notification.platform == "email"
            ).order_by(Notification.received_at.desc()).first()

            if not latest_msg:
                continue

            email_script = await get_email_formatted_context(db, latest_msg)
            ai_result = await analyze_email_context(email_script)

            if ai_result:
                sender_email = latest_msg.external_sender_id or "unknown@domain.com"
                extracted_topic = ai_result.summary[:50] if (
                            hasattr(ai_result, 'summary') and ai_result.summary) else clean_subject

                fusion_result = orchestrator.resolve_priority(
                    account_id=account_id,
                    notification_id=latest_msg.id,
                    external_sender_id=sender_email,
                    ai_score=ai_result.priority_score,
                    current_topic=extracted_topic,
                    platform="email"
                )

                analysis = db.query(EmailAnalysis).filter_by(notification_id=latest_msg.id).first()
                if not analysis:
                    analysis = EmailAnalysis(notification_id=latest_msg.id)
                    db.add(analysis)

                if hasattr(ai_result, 'category_id'):
                    analysis.category_id = ai_result.category_id
                if hasattr(ai_result, 'summary'):
                    analysis.summary = ai_result.summary

                analysis.priority_score = fusion_result['final_priority']

                db.query(Notification).filter(
                    Notification.subject == subject,
                    Notification.account_id == account_id,
                    Notification.status == "pending",
                    Notification.platform == "email"
                ).update({"status": "processed"})

                processed_threads_count += 1
                logger.debug(f"✅ 邮件 Thread [{clean_subject}] 已成功闭环修约。")
            else:
                logger.warning(f"⚠️ AI 响应无法提取有效特征，邮件 Thread [{clean_subject}] 暂不闭环。")

        except Exception as e:
            logger.error(f"❌ 处理邮件 Thread [{subject}] 失败: {e}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"💥 数据库提交失败，事务已回滚: {e}")
        return 0

    return processed_threads_count