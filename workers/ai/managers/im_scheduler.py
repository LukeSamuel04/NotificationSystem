# workers/ai/managers/im_scheduler.py
import asyncio
import logging

# 引入数据库连接池生成器 (请根据你的项目结构调整路径)
from app.db.session import SessionLocal

# 💥 引入咱们的纯粹干活的 Executor
from workers.ai.managers.im_executor import process_pending_im_sessions

logger = logging.getLogger("IMScheduler")

# ==========================================
# 1. 全局信号开关 (Webhook 的专属门铃)
# ==========================================
_scan_trigger = asyncio.Event()


def trigger_immediate_scan():
    """暴露给外部 Webhook 的接口，用于打断休眠，立即触发扫盘"""
    _scan_trigger.set()


# ==========================================
# 2. 扫盘统筹动作
# ==========================================
async def perform_scan():
    """
    负责统筹 IM 业务线的一次完整扫盘动作
    """
    logger.debug("🔍 IM 调度器：开始执行数据库扫盘...")

    # 💥 关键点：每次扫盘必须从连接池拿一个新的 Session，用完即焚
    db = SessionLocal()
    try:
        # 把数据库会话交给 Executor 去干脏活累活
        processed_count = await process_pending_im_sessions(db)

        if processed_count and processed_count > 0:
            logger.info(f"✅ IM 调度器：本轮扫盘结束，共处理 {processed_count} 个会话。")

    except Exception as e:
        logger.error(f"❌ IM 调度器：扫盘任务执行过程中发生异常: {e}")
    finally:
        # 💥 关键点：无论成功失败，必须释放连接，防止 24 小时后台运行撑爆数据库
        db.close()


# ==========================================
# 3. 守护进程主循环 (死循环)
# ==========================================
async def start_im_scheduler():
    """
    IM 后台调度中心的主循环
    """
    logger.info("🚀 IM Scheduler (调度中心) 已启动，进入 24 小时待命状态！")

    # 1. 服务刚启动时，先无条件扫盘一次，清理历史积压
    await perform_scan()

    # 2. 进入永不停止的死循环
    while True:
        try:
            # 核心魔法：最多等 30 秒。
            # 如果 Webhook 按了门铃 (_scan_trigger.set())，瞬间醒来。
            # 如果 30 秒没人按门铃，抛出 TimeoutError，执行常规巡逻。
            await asyncio.wait_for(_scan_trigger.wait(), timeout=30.0)

            logger.info("⚡ 接收到 Webhook 紧急信号，立即触发扫盘！")

            # 醒来后，把门铃复位，准备迎接下一次信号
            _scan_trigger.clear()

        except asyncio.TimeoutError:
            # 30 秒到了没人叫它，执行兜底巡逻
            logger.debug("⏱️ 30秒兜底巡逻触发...")
            pass

        except Exception as e:
            # 防御性编程：万一循环本身挂了，睡 5 秒防死锁
            logger.error(f"💥 Scheduler 循环发生严重错误: {e}")
            await asyncio.sleep(5)

            # 无论是被 Webhook 唤醒，还是 30 秒自然醒，都去执行扫盘
        await perform_scan()