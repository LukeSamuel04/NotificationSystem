# workers/ai/managers/email_executor.py
import logging
from sqlalchemy.orm import Session

# 导入底层数据模型
from app.models.notifications import Notification
from app.models.account import FetchAccount
from app.models.email_analysis import EmailAnalysis  # 假设你存放 category、score 的表

# 💥 引入 Email 专用的上下文服务与 AI 算分模型
from app.services.context.email.manager import get_email_formatted_context
from workers.ai.models.email.scorer import analyze_email_context

logger = logging.getLogger("EmailExecutor")


async def process_pending_emails(db: Session) -> int:
    """
    【Email 专线流水线】
    1. 按照 (账号, 主题) 分组，确保同一个长 Thread 内的多次未读邮件只触发一次最新分析。
    2. 将生成的 7 维分类 ID 和行动指令摘要存入分析表。
    3. 批量将该 Thread 下所有 pending 的邮件全部置为 processed。
    """
    # 1. 捞取名单：以 subject 为聚合维度 (应对密集邮件轰炸)
    pending_threads = db.query(
        Notification.subject,
        Notification.account_id
    ).filter(
        Notification.status == "pending",
        Notification.platform == "email"
    ).distinct().all()

    if not pending_threads:
        return 0

    processed_threads_count = 0

    for subject, account_id in pending_threads:
        try:
            # 2. 账号合法性守卫：验证该收件人所属的系统账号是否依然在绑定列表中
            valid_account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
            if not valid_account:
                logger.warning(f"⚠️ 拦截到无效账号消息：账号 {account_id} 未绑定或已失效，跳过处理。")
                continue

            clean_subject = subject or "无主题"
            logger.info(f"🔍 正在处理邮件 Thread [账号: {account_id} | 主题: {clean_subject}]...")

            # 3. 定位时间锚点：获取该 Thread 下最新的一条 pending 邮件
            latest_msg = db.query(Notification).filter(
                Notification.subject == subject,
                Notification.account_id == account_id,
                Notification.status == "pending",
                Notification.platform == "email"
            ).order_by(Notification.received_at.desc()).first()

            if not latest_msg:
                continue

            # 4. 提取剧本：包含双向互动历史的纯净剧本
            email_script = await get_email_formatted_context(db, latest_msg)

            # 5. 召唤 AI：基于 7 维分类法进行智能总结与算分
            ai_result = await analyze_email_context(email_script)

            if ai_result:
                # 6. UPSERT 逻辑：存储 AI 分析结果
                analysis = db.query(EmailAnalysis).filter(
                    EmailAnalysis.notification_id == latest_msg.id
                ).first()

                if not analysis:
                    analysis = EmailAnalysis(notification_id=latest_msg.id)
                    db.add(analysis)

                # 映射：将返回的 category_id 存入 Schema 暴露的字段中
                # 如果你的 category 字段定义为 Integer，这里可以直接赋值 ai_result.category_id
                analysis.category_id = ai_result.category_id
                analysis.priority_score = ai_result.priority_score
                analysis.summary = ai_result.summary

                # 7. 批量放行：将该 Thread 下所有 pending 的邮件全部置为 processed
                # 💥 核心防爆机制：一晚上收到 10 封 GitHub Issue 通知，只会在最后 1 封算分，然后全部放行！
                db.query(Notification).filter(
                    Notification.subject == subject,
                    Notification.account_id == account_id,
                    Notification.status == "pending",
                    Notification.platform == "email"
                ).update({"status": "processed"})

                processed_threads_count += 1
                logger.debug(f"✅ 邮件 Thread [{clean_subject}] 已成功闭环，分类为: {ai_result.category_id}")

            else:
                logger.warning(f"⚠️ AI 未能给出有效分析，邮件 Thread [{clean_subject}] 暂不闭环。")

        except Exception as e:
            logger.error(f"❌ 处理邮件 Thread [{subject}] 时发生严重异常: {e}")

    try:
        # 8. 事务提交
        db.commit()
        if processed_threads_count > 0:
            logger.info(f"🎉 任务完成：本轮合并处理并闭环了 {processed_threads_count} 个邮件 Thread。")
    except Exception as e:
        db.rollback()
        logger.error(f"💥 数据库提交失败，已回滚事务: {e}")
        return 0

    return processed_threads_count