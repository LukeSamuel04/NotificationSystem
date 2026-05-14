# test/test_real_email_pipeline.py
import asyncio
import sys
import os
import logging
from sqlalchemy.orm import Session

# 💥 全局日志探头：实时观测云端交互与 AI 推理细节
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
# 屏蔽底层协议层的冗余通讯日志
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("aioimaplib").setLevel(logging.WARNING)

# 动态挂载项目根目录
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.account import FetchAccount
from app.models.notifications import Notification
from app.models.email_analysis import EmailAnalysis

# 引入核心业务组件
from workers.notification.fetch_manager import fetch_messages_for_account, process_and_save_message
from workers.ai.managers.email_scheduler import start_email_scheduler, trigger_email_scan


async def wait_for_pipeline_completion(target_msg_ids: list[int], timeout_seconds: int = 60) -> bool:
    """轮询器：监控这批生肉邮件是否已被 AI 消化完毕"""
    logger = logging.getLogger("PipelineMonitor")
    for _ in range(timeout_seconds):
        with SessionLocal() as check_db:
            pending_count = check_db.query(Notification).filter(
                Notification.id.in_(target_msg_ids),
                Notification.status == "pending"
            ).count()

            if pending_count == 0:
                return True
        await asyncio.sleep(1)
    return False


async def run_real_pipeline_test():
    logger = logging.getLogger("RealPipelineTest")
    logger.info("==================================================")
    logger.info("🌟 执行全自动化生产级链路测试 (基于数据库激活账号) 🌟")
    logger.info("==================================================")

    db: Session = SessionLocal()
    newly_saved_msg_ids = []

    try:
        # --------------------------------------------------------------------------
        # 步骤一：自动检索数据库中的“激活”邮箱账号
        # --------------------------------------------------------------------------
        logger.info("🔍 [步骤一] 正在从数据库检索已激活的 Email 账号...")

        # 自动捞取第一个激活且有效的邮箱账号
        account = db.query(FetchAccount).filter(
            FetchAccount.platform == "email",
            FetchAccount.is_active == True,
            FetchAccount.is_valid == True
        ).first()

        if not account:
            logger.error("\n❌ 错误：数据库中未找到任何已激活的 Email 账号！")
            logger.info("💡 请先确保数据库 fetch_accounts 表中已有可用记录，且 is_active 和 is_valid 均为 1。")
            return

        logger.info(f"✅ 成功命中活跃账号: {account.username} [ID: {account.id}]")

        # --------------------------------------------------------------------------
        # 步骤二：执行真实云端抓取 (Fetcher -> Manager)
        # --------------------------------------------------------------------------
        logger.info(f"\n🌐 [步骤二] 正在呼叫抓取引擎连接至云端服务器...")

        # 这里会调用 fetch_manager，它会自动读取 account.config 里的 host 和 password
        raw_messages = await fetch_messages_for_account(account)

        if not raw_messages:
            logger.warning("\n⚠️ 抓取结果为空！")
            logger.warning("💡 提示：该账号下目前可能没有‘未读’邮件。请发一封测试信或手动在邮箱里将邮件设为‘未读’。")
            return

        logger.info(f"📦 成功拉取到 {len(raw_messages)} 封目标邮件，准备执行清洗与落盘...")

        # --------------------------------------------------------------------------
        # 步骤三：清洗并安全落盘 (生肉层)
        # --------------------------------------------------------------------------
        for raw_msg in raw_messages:
            # 模拟真实线程安全环境入库
            saved_msg = await asyncio.to_thread(process_and_save_message, db, account, raw_msg)
            if saved_msg:
                newly_saved_msg_ids.append(saved_msg.id)
                logger.info(f"   └── ✅ 新记录入库 [ID: {saved_msg.id} | 主题: {saved_msg.subject[:20]}...]")
            else:
                logger.debug(f"   └── 过滤已存在的重复邮件: {raw_msg.get('subject')}")

        if not newly_saved_msg_ids:
            logger.info("ℹ️ 本轮抓取的邮件在数据库中均已存在，无需触发 AI 分析。")
            return

        # --------------------------------------------------------------------------
        # 步骤四：激活 AI 矩阵 (Direct Trigger)
        # --------------------------------------------------------------------------
        logger.info(f"\n🚀 [步骤四] 启动 Email Scheduler 守护进程并隔空按响门铃...")

        # 后台运行 AI 调度器
        scheduler_task = asyncio.create_task(start_email_scheduler())

        # 💥 瞬间触发！
        trigger_email_scan()

        # 等待熟肉产出
        success = await wait_for_pipeline_completion(newly_saved_msg_ids)

        if success:
            logger.info("\n🎉 链路闭环！AI 已完成对这批新邮件的深度分析。")

            # --------------------------------------------------------------------------
            # 步骤五：熟肉成果检视
            # --------------------------------------------------------------------------
            logger.info("\n📊 [最终熟肉产出报告]")
            analyses = db.query(EmailAnalysis).filter(EmailAnalysis.notification_id.in_(newly_saved_msg_ids)).all()
            for ana in analyses:
                parent = db.query(Notification).filter(Notification.id == ana.notification_id).first()
                title = parent.subject if parent else "未知主题"
                logger.info(f"   ├── 📧 {title}")
                logger.info(f"   │   ├── 分数: {ana.priority_score} | 分类: {ana.category_id}")
                logger.info(f"   │   └── AI 摘要: {ana.summary}")
                logger.info("   " + "-" * 45)

            logger.info("\n✨ 测试圆满结束！数据已留存数据库，快去开发前端看板吧！")

        else:
            logger.error("\n❌ 链路处理超时，请检查 Executor 或大模型连接日志。")

    except Exception as e:
        logger.error(f"💥 全自动化集成测试遭遇崩溃: {e}", exc_info=True)

    finally:
        if 'scheduler_task' in locals() and not scheduler_task.done():
            scheduler_task.cancel()
        db.close()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_real_pipeline_test())