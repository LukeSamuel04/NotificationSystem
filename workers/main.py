import asyncio
import logging
import sys

# 引入三大兵营的主循环
# 注意：请确保这些导入路径与你的实际文件路径完全一致
from workers.account.availability_tester import tester_loop
from workers.notification.fetch_manager import fetch_loop
from workers.ai.ai_manager import ai_loop

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SystemMain")


async def main():
    logger.info("========================================")
    logger.info("🌟 分布式后台引擎 (Workers) 正在启动 🌟")
    logger.info("========================================")

    # 1. 制造“进程级”全局遥控器：优雅关机信号
    stop_event = asyncio.Event()
    # 2. 制造“业务级”专线对讲机：数据唤醒信号
    new_data_event = asyncio.Event()

    # 3. 将三大战将拉起，分配遥控器和对讲机
    logger.info("正在唤醒三大战将...")

    # 启动心跳探针 (独立运行，只需要停机遥控器，这里假设你的函数也改成了接受 stop_event)
    tester_task = asyncio.create_task(tester_loop(stop_event))

    # 启动抓取引擎 (采购员：拿到遥控器 + 对讲机发射端)
    # 设定每 60 秒巡视一次全网账号
    fetch_task = asyncio.create_task(fetch_loop(stop_event, new_data_event, poll_interval=60))

    # 启动 AI 算分引擎 (扫地僧：拿到遥控器 + 对讲机接收端)
    ai_task = asyncio.create_task(ai_loop(stop_event, new_data_event))

    try:
        # 主线程在这里“挂机”，维持整个异步宇宙的运转
        logger.info("✅ 所有引擎已成功挂载！系统进入自动巡航模式。")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        # 4. 拦截 Ctrl+C 或 Docker stop 信号
        logger.warning("\n⚠️ 接收到退出指令 (KeyboardInterrupt)！准备优雅停机...")

        # 第一步：按下全局停止按钮，通知所有引擎准备下线
        stop_event.set()

        # 💥 架构师细节：必须同时按下数据唤醒按钮！
        # 因为 AI 引擎此时可能正在死等 new_data_event 唤醒。
        # 按下它，让 AI 瞬间醒来，从而立刻查看到 stop_event 已亮起，光速安全下线。
        new_data_event.set()

        logger.info("正在等待所有引擎完成手头的数据库收尾工作 (请勿强退)...")

        # 等待所有任务安全退出，保证不产生任何数据库脏数据
        await asyncio.gather(tester_task, fetch_task, ai_task)

        logger.info("🛑 所有后台引擎已安全切断电源。Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    # 启动异步宇宙
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # 兜底捕获，防止 Python 抛出刺眼的报错堆栈
        pass