#重构之后将作废
# workers/ai/ai_manager.py
import asyncio
import logging
from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal

from app.models.notifications import Notification
from app.models.analysis import NotificationAnalysis
from app.models.account import FetchAccount

from workers.ai.models.email.scorer_local import analyze_email_priority

logger = logging.getLogger("AIManager")


async def process_pending_notifications(db: Session, batch_size: int = 50) -> int:
    """【已路由化 & 异步化】扫描待处理数据，进行 AI 算分"""
    pending_msgs = db.query(Notification) \
        .options(joinedload(Notification.account)) \
        .filter(Notification.status == "pending") \
        .limit(batch_size) \
        .all()

    if not pending_msgs:
        return 0

    logger.info(f"⚙️ 捞取到 {len(pending_msgs)} 条待处理消息，开始智能路由与 AI 算分...")
    processed_count = 0

    for msg in pending_msgs:
        try:
            if not msg.account:
                logger.error(f"❌ 消息 {msg.id} 找不到关联的账号信息，无法判断平台。")
                msg.status = "error"
                continue

            platform = msg.account.platform.lower()
            ai_result = None

            if platform == 'email':
                ai_result = await asyncio.to_thread(
                    analyze_email_priority,
                    subject=msg.subject or "",
                    content=msg.cleaned_content or ""
                )
            elif platform in ['instagram', 'whatsapp']:
                logger.info(f"🚧 平台 [{platform.upper()}] 的 AI 模型尚未挂载，跳过评分。")
                continue
            else:
                logger.warning(f"❓ 未知平台 [{platform}]，无法路由到对应的 AI 模型。")
                msg.status = "error"
                continue

            if ai_result:
                analysis_record = NotificationAnalysis(
                    notification_id=msg.id,
                    priority_score=ai_result.get("priority_score"),
                    category=ai_result.get("category"),
                    summary=ai_result.get("summary")
                )
                db.add(analysis_record)

                msg.status = "unread"
                processed_count += 1
            else:
                logger.warning(f"⚠️ 消息 {msg.id} AI 分析未返回有效结果")
                msg.status = "error"

        except Exception as e:
            logger.error(f"❌ 处理消息 ID {msg.id} 时发生错误: {e}")
            msg.status = "error"

    try:
        db.commit()
        logger.info(f"✅ 成功完成 {processed_count} 条消息的 AI 算分并入库！")
    except Exception as e:
        db.rollback()
        logger.error(f"💥 数据库保存失败，已回滚: {e}")
        return 0

    return processed_count


# 💥 架构升级：引入 new_data_event 事件驱动
async def ai_loop(stop_event: asyncio.Event, new_data_event: asyncio.Event):
    logger.info("🤖 AI 质检中心启动！进入扫地僧模式，先清空历史积压...")

    while not stop_event.is_set():
        db = SessionLocal()
        try:
            processed_count = await process_pending_notifications(db, batch_size=50)

            if processed_count > 0:
                # 💥 只要还有积压，坚决不睡，连轴转！
                logger.info("🔥 发现库里还有积压数据，继续全速扫盘...")
                await asyncio.sleep(0.5)  # 仅做极其微小的让步，防 CPU 100% 卡死
                continue

            else:
                # 💥 扫盘彻底干净了！重置对讲机，准备进入深度休眠
                logger.info("📭 数据库已完全干净。重置对讲机，挂起休眠...")
                new_data_event.clear()

        except Exception as e:
            logger.error(f"🔥 AI Worker 遇到致命错误: {e}")
            await asyncio.sleep(5)  # 报错了就缓一口气，再试
        finally:
            db.close()

        # 💥 深度挂起监听：死等 new_data_event 发信号！
        # 但我们用 timeout=60 防御性编程，每分钟微睁眼看一次关机信号，以免死锁
        try:
            await asyncio.wait_for(new_data_event.wait(), timeout=60)
            if new_data_event.is_set():
                 logger.info("⚡ 收到抓取引擎对讲机呼叫，AI 瞬间唤醒！")
        except asyncio.TimeoutError:
            # 60秒都没人叫我，没关系，进入下一个 while 循环看一眼关机灯，继续扫盘/睡
            pass

    logger.info("🛑 AI 质检中心收到停机信号，安全下线。")