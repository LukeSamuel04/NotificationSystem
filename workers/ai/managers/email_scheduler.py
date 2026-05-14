# workers/ai/managers/email_scheduler.py
import asyncio
import logging

# 引入数据库连接池生成器
from app.db.session import SessionLocal

# 💥 引入专职干活的 Email 算分流水线执行器
from workers.ai.managers.email_executor import process_pending_emails

logger = logging.getLogger("EmailScheduler")

# =====================================================================
# 1. 全局信号开关 (拉取脚本/IMAP IDLE 监听器的专属门铃)
# =====================================================================
_email_scan_trigger = asyncio.Event()


def trigger_email_scan():
    """
    暴露给外部收件模块（如 IMAP 轮询服务或新邮件拉取脚本）的接口。
    一旦底层成功将新邮件落盘入库，立即按响此门铃，唤醒 AI 执行流水线。
    """
    _email_scan_trigger.set()


# =====================================================================
# 2. 扫盘统筹动作
# =====================================================================
async def perform_email_scan():
    """
    统筹邮件业务线的一次完整扫盘与闭环动作
    """
    logger.debug("🔍 Email 调度器：开始执行邮件待办扫盘...")

    # 💥 关键守卫：每次扫盘从连接池获取独立 Session，确保线程/协程安全
    db = SessionLocal()
    try:
        # 移交数据库会话给 Executor 执行长文本聚合与 LLM 推理
        processed_threads = await process_pending_emails(db)

        if processed_threads and processed_threads > 0:
            logger.info(f"✅ Email 调度器：本轮扫盘结束，成功归档并闭环了 {processed_threads} 个邮件 Thread。")

    except Exception as e:
        logger.error(f"❌ Email 调度器：执行邮件算分任务时发生严重异常: {e}")
    finally:
        # 💥 绝对规则：用完即焚，立刻释放连接回池，防止造成连接泄露
        db.close()


# =====================================================================
# 3. 守护进程主循环 (后台死循环待命)
# =====================================================================
async def start_email_scheduler():
    """
    Email 后台智能处理调度中心的主循环
    """
    logger.info("🚀 Email Scheduler (邮件智能调度中心) 已启动，进入全天候轮询与监听状态！")

    # 1. 启动初期：无条件扫盘一次，清空服务宕机或重启期间积压的未处理邮件
    await perform_email_scan()

    # 2. 进入永恒的守护循环
    while True:
        try:
            # 核心机制：默认挂起等待 30 秒。
            # 场景 A: 如果新邮件收取脚本调用了 trigger_email_scan()，瞬间被唤醒。
            # 场景 B: 30 秒内无事发生，触发超时，平滑执行兜底扫盘。
            await asyncio.wait_for(_email_scan_trigger.wait(), timeout=30.0)

            logger.info("⚡ 接收到新邮件落盘入库信号，立即触发 AI 深度解析！")

            # 唤醒后立刻重位触发器，准备接收下一次唤醒脉冲
            _email_scan_trigger.clear()

        except asyncio.TimeoutError:
            # 静默超时触发常规防线巡逻
            logger.debug("⏱️ 邮件 30秒 兜底定时巡逻触发...")
            pass

        except Exception as e:
            # 防御性静默恢复：避免未知代码级崩溃引发死循环雪崩
            logger.error(f"💥 Email Scheduler 守护协程意外中断: {e}")
            await asyncio.sleep(5)

        # 无论由哪种途径触发，统一进入核心扫盘闭环
        await perform_email_scan()