# workers/ai/managers/im_executor.py
import logging
from sqlalchemy.orm import Session

# 导入底层数据模型
from app.models.notifications import Notification
from app.models.im_session import IMSessionState
from app.models.account import FetchAccount  # 💥 新增：用于验证账号绑定状态

# 导入上下文服务与 AI 算分模型
from app.services.context.manager import get_formatted_context
from workers.ai.models.social_media.scorer import analyze_social_media_session # 修正了之前的拼写错误

logger = logging.getLogger("IMManager")


async def process_pending_im_sessions(db: Session) -> int:
    """
    【IM 专线流水线 V2】
    1. 移除消息方向过滤，确保我方发送的消息也能触发并参与 AI 上下文分析。
    2. 增加账号合法性校验，仅为系统中真实绑定的收件账号维护会话档案。
    """
    # 1. 捞取名单：移除 is_from_me 过滤，允许我方回复的消息也作为“并集”的一部分触发更新
    pending_sessions = db.query(
        Notification.external_sender_id,
        Notification.account_id,
        Notification.platform
    ).filter(
        Notification.status == "pending"
    ).distinct().all()

    if not pending_sessions:
        return 0

    processed_users_count = 0

    for sender_id, account_id, platform in pending_sessions:
        try:
            # 💥 2. 账号合法性守卫：验证该收件人所属的系统账号是否依然在绑定列表中
            valid_account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
            if not valid_account:
                logger.warning(f"⚠️ 拦截到无效账号消息：账号 {account_id} 未绑定或已失效，跳过会话处理。")
                # 可选：将这些消息标记为 error 或忽略，防止下次扫盘重复捞取
                continue

            logger.info(f"🔍 正在处理窗口 [发件人: {sender_id} -> 系统账号: {account_id}]...")

            # 3. 定位时间锚点：获取该窗口下最新的一条待处理消息（不论是我发的还是对方发的）
            latest_msg = db.query(Notification).filter(
                Notification.external_sender_id == sender_id,
                Notification.account_id == account_id,
                Notification.status == "pending"
            ).order_by(Notification.received_at.desc()).first()

            if not latest_msg:
                continue

            # 4. 提取剧本：此时生成的 Context 剧本将包含最新的双向互动内容
            chat_context_script = await get_formatted_context(db, latest_msg)

            # 5. 召唤 AI：基于双向对话进行全局总结与算分
            ai_result = await analyze_social_media_session(chat_context_script)

            if ai_result:
                # 6. UPSERT 逻辑：更新或创建会话状态记录
                session_state = db.query(IMSessionState).filter(
                    IMSessionState.external_sender_id == sender_id,
                    IMSessionState.account_id == account_id
                ).first()

                if not session_state:
                    # 只有通过了第 2 步校验的账号才有资格创建档案
                    session_state = IMSessionState(
                        external_sender_id=sender_id,
                        account_id=account_id,
                        platform=platform
                    )
                    db.add(session_state)

                # 更新由 AI 汲取的最新情报
                session_state.current_topic = ai_result.current_topic
                session_state.priority_score = ai_result.priority_score
                session_state.summary_snapshot = ai_result.summary_snapshot
                session_state.last_message_at = latest_msg.received_at

                # 7. 批量放行：将该窗口下所有 pending 的双向消息全部置为 processed
                db.query(Notification).filter(
                    Notification.external_sender_id == sender_id,
                    Notification.account_id == account_id,
                    Notification.status == "pending"
                ).update({"status": "processed"})

                processed_users_count += 1
                logger.debug(f"✅ 窗口 [{sender_id}] 已成功更新会话环境。")

            else:
                logger.warning(f"⚠️ AI 未能给出有效分析，用户 [{sender_id}] 的消息暂不闭环。")

        except Exception as e:
            logger.error(f"❌ 处理窗口 [{sender_id}] 时发生严重异常: {e}")

    try:
        # 8. 事务提交
        db.commit()
        if processed_users_count > 0:
            logger.info(f"🎉 任务完成：本轮共同步并更新了 {processed_users_count} 个合法的 IM 会话环境。")
    except Exception as e:
        db.rollback()
        logger.error(f"💥 数据库提交失败，已回滚事务: {e}")
        return 0

    return processed_users_count