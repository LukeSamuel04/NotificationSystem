# workers/ai/managers/im_executor.py
import logging
from sqlalchemy.orm import Session

# 导入底层数据模型
from app.models.notifications import Notification
from app.models.im_session import IMSessionState
from app.models.account import FetchAccount

# 导入上下文服务与 AI 算分模型
from app.services.context.manager import get_formatted_context
from workers.ai.models.social_media.scorer import analyze_social_media_session

# 💥 引入核心融合大脑
from app.services.local_scoring.priority_orchestrator import PriorityOrchestrator

logger = logging.getLogger("IMManager")


async def process_pending_im_sessions(db: Session) -> int:
    """
    【IM 专线流水线 V3 终极加固版】
    1. 引入运行时强转装甲：强制隔离弱类型数据库驱动层返回的游标基础类型断层。
    2. 显式生命周期管理：AI 评估前置开辟热表环境，确保底层指针寻址安全。
    3. 接入 PriorityOrchestrator 实现综合多路因子平滑与冷表深度留痕。
    """
    pending_sessions = db.query(
        Notification.external_sender_id,
        Notification.account_id,
        Notification.platform
    ).filter(
        Notification.status == "pending",
        Notification.platform == "instagram"
    ).distinct().all()

    if not pending_sessions:
        return 0

    orchestrator = PriorityOrchestrator(db)
    processed_users_count = 0

    for sender_id, raw_account_id, platform in pending_sessions:
        try:
            # 💥 运行时防御装甲：无论游标吐出 int 还是 str，内存空间一律抹平为安全纯字符串
            account_id = str(raw_account_id)

            valid_account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
            if not valid_account:
                logger.warning(f"⚠️ 守卫拦截：接收账号 {account_id} 未绑定或已失效，跳过该载荷。")
                continue

            if not sender_id or sender_id.startswith("system_"):
                continue

            latest_msg = db.query(Notification).filter(
                Notification.external_sender_id == sender_id,
                Notification.account_id == account_id,
                Notification.status == "pending"
            ).order_by(Notification.received_at.desc()).first()

            if not latest_msg:
                continue

            # -----------------------------------------------------------------
            # 💥 前置显式生命周期控制：查询并按需安全建档
            # -----------------------------------------------------------------
            session_state = db.query(IMSessionState).filter_by(
                external_sender_id=sender_id,
                account_id=account_id
            ).first()

            if not session_state:
                logger.info(f"✨ 网关放行：正在为新窗口 [{sender_id}] 显式建档...")
                session_state = IMSessionState(
                    external_sender_id=sender_id,
                    account_id=account_id,
                    platform=platform,
                    priority_score=1
                )
                db.add(session_state)
                # 此时全内存对象主键槽位类型高度一致，安全推入底层
                db.flush()

            chat_context_script = await get_formatted_context(db, latest_msg)
            ai_result = await analyze_social_media_session(chat_context_script)

            if ai_result:
                fusion_result = orchestrator.resolve_priority(
                    account_id=account_id,
                    notification_id=latest_msg.id,
                    external_sender_id=sender_id,
                    ai_score=ai_result.priority_score,
                    current_topic=ai_result.current_topic,
                    platform=platform
                )

                if hasattr(ai_result, 'summary_snapshot') and hasattr(session_state, 'summary_snapshot'):
                    session_state.summary_snapshot = ai_result.summary_snapshot
                if hasattr(session_state, 'last_message_at'):
                    session_state.last_message_at = latest_msg.received_at

                db.query(Notification).filter(
                    Notification.external_sender_id == sender_id,
                    Notification.account_id == account_id,
                    Notification.status == "pending"
                ).update({"status": "processed"})

                processed_users_count += 1
                logger.debug(f"✅ 窗口 [{sender_id}] 调度闭环完成。综合优先级: {fusion_result['final_priority']}")
            else:
                logger.warning(f"⚠️ AI 响应解析失败，发件人 [{sender_id}] 的消息暂不闭环。")

        except Exception as e:
            logger.error(f"❌ 处理窗口 [{sender_id}] 时发生严重异常: {e}")

    try:
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"💥 数据库提交失败，事务已回滚: {e}")
        return 0

    return processed_users_count