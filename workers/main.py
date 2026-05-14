# workers/main.py
import asyncio
import logging
import sys

# 1. 引入账号巡视与抓取引擎
from workers.account.availability_tester import tester_loop
from workers.notification.fetch_manager import fetch_loop

# 2. 引入全新的全渠道并发 AI 矩阵 (已对齐新架构)
from workers.ai.managers.im_scheduler import start_im_scheduler
from workers.ai.managers.email_scheduler import start_email_scheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemMatrix")


async def main():
    logger.info("==================================================")
    logger.info("🌟 全渠道分布式后台矩阵 (Workers Matrix) 正在启动 🌟")
    logger.info("==================================================")

    # 全局遥控器：优雅关机信号
    stop_event = asyncio.Event()
    # 业务对讲机：数据唤醒信号（fetch_loop 仍会设置它以保持兼容）
    new_data_event = asyncio.Event()

    logger.info("正在部署各战区守护协程...")

    # --- 战区一：账号心跳巡视 (Tester) ---
    # 负责定时检查所有绑定账号（如邮箱 IMAP、IG Token）是否依然可用
    tester_task = asyncio.create_task(
        tester_loop(stop_event),
        name="AccountTesterTask"
    )

    # --- 战区二：新数据采购员 (Fetcher) ---
    # 负责每 60 秒主动扫盘（邮件等），发现新数据后直接 trigger 下游
    fetch_task = asyncio.create_task(
        fetch_loop(stop_event, new_data_event, poll_interval=60),
        name="FetchManagerTask"
    )

    # --- 战区三：IM 熟肉加工厂 (IM Scheduler) ---
    # 24小时待命，等待 Webhook 路由直接触发 trigger_immediate_scan()
    im_ai_task = asyncio.create_task(
        start_im_scheduler(),
        name="IMSchedulerTask"
    )

    # --- 战区四：Email 熟肉加工厂 (Email Scheduler) ---
    # 24小时待命，等待 fetch_loop 抓到新邮件后直接 trigger_email_scan()
    email_ai_task = asyncio.create_task(
        start_email_scheduler(),
        name="EmailSchedulerTask"
    )

    try:
        logger.info("✅ 矩阵组网完成！全线进入并发自动巡航模式。")
        # 主线程在此挂起，守护以上四个并发任务
        await asyncio.gather(
            tester_task,
            fetch_task,
            im_ai_task,
            email_ai_task
        )

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.warning("\n⚠️ 接收到物理级退出指令！准备优雅停机...")

        # 按下全局停止按钮
        stop_event.set()
        # 顺便按下唤醒按钮，防止有的引擎在死等新数据时卡住
        new_data_event.set()

        logger.info("正在回收所有资源并等待数据库收尾工作...")

        # 取消新版 AI 任务（因为它们是死循环，需要手动 cancel）
        im_ai_task.cancel()
        email_ai_task.cancel()

        # 等待所有战将安全撤离
        await asyncio.gather(
            tester_task,
            fetch_task,
            im_ai_task,
            email_ai_task,
            return_exceptions=True
        )

        logger.info("🛑 矩阵电源已切断。Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass