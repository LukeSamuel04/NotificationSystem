# test/test_im_scheduler.py
import asyncio
import sys
import os
import uuid
import logging
from datetime import datetime, timedelta
from app.models.email_analysis import EmailAnalysis

# 💥 打开全局探头：将所有的日志强制输出到控制台，以便我们看清后台到底发生了什么
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# 屏蔽掉一些底层的噪音日志（比如网络请求库的底层日志）
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.account import FetchAccount
from app.models.notifications import Notification

# 导入我们的“包工头”和“门铃”
from workers.ai.managers.im_scheduler import start_im_scheduler, trigger_immediate_scan


async def wait_for_processed(msg_id: str, timeout_seconds: int = 30) -> bool:
    """动态轮询器：每次用全新的数据库连接去查，彻底避开事务隔离导致的幻读问题"""
    for _ in range(timeout_seconds):
        # 💥 核心修复：用 with 语法每次开启一个全新的 Session，查完立刻释放
        # 这样就能读到数据库里最真实、最新的已提交数据
        with SessionLocal() as check_db:
            msg = check_db.query(Notification).filter(Notification.account_msg_id == msg_id).first()
            if msg and msg.status == "processed":
                return True
        await asyncio.sleep(1)
    return False


async def run_scheduler_test():
    # 主线程专用的 db，仅用于造数据和删数据
    db = SessionLocal()

    test_account_id = 888888
    test_platform_id = f"test_ig_{uuid.uuid4().hex[:8]}"
    test_external_sender_id = f"test_user_{uuid.uuid4().hex[:8]}"

    msg1_id = f"msg_old_{uuid.uuid4().hex[:4]}"
    msg2_id = f"msg_new_{uuid.uuid4().hex[:4]}"

    print("🛠️ [准备阶段] 初始化测试环境...")
    try:
        # 1. 创建测试账号
        temp_account = FetchAccount(
            id=test_account_id,
            platform="instagram",
            platform_account_id=test_platform_id,
            username="Scheduler Test Account",
            config={"env": "test"}
        )
        db.add(temp_account)
        db.commit()

        # ==========================================
        # 🎬 第一幕：测试“启动即扫盘 (清理残留)”
        # ==========================================
        print("\n🎬 [第一幕] 模拟系统宕机恢复后的残留数据...")
        msg1 = Notification(
            account_id=test_account_id,
            platform="instagram",
            account_msg_id=msg1_id,
            sender="IG User",
            external_sender_id=test_external_sender_id,
            cleaned_content="这是昨天半夜发来的消息，系统当时没开。",
            is_from_me=False,
            received_at=datetime.now() - timedelta(hours=8),
            status="pending"
        )
        db.add(msg1)
        db.commit()

        print("🚀 启动后台 Scheduler 守护进程...")
        # 将死循环函数封装成后台任务，不阻塞主线程往下走
        scheduler_task = asyncio.create_task(start_im_scheduler())

        print("⏳ 等待 Scheduler 完成初始启动扫盘...")
        # 注意：这里已经去掉了 db 参数
        success = await wait_for_processed(msg1_id)
        if success:
            print("✅ 第一幕成功：Scheduler 刚启动就完美清空了历史残留数据！")
        else:
            print("❌ 第一幕失败：残留数据未被处理，或处理超时。")

        # ==========================================
        # 🎬 第二幕：测试“Webhook 瞬间唤醒”
        # ==========================================
        print("\n🎬 [第二幕] 模拟系统平稳运行中，突然收到 Webhook 新消息...")
        msg2 = Notification(
            account_id=test_account_id,
            platform="instagram",
            account_msg_id=msg2_id,
            sender="IG User",
            external_sender_id=test_external_sender_id,
            cleaned_content="嘿！刚才的测试通过了吗？",
            is_from_me=False,
            received_at=datetime.now(),
            status="pending"
        )
        db.add(msg2)
        db.commit()

        print("🔔 叮咚！Webhook 接收到数据，瞬间按下唤醒门铃！")
        trigger_immediate_scan()

        print("⏳ 盯着数据库，看 Scheduler 是否能在睡眠中被瞬间踢醒...")
        # 注意：这里也去掉了 db 参数
        success = await wait_for_processed(msg2_id)
        if success:
            print("✅ 第二幕成功：Scheduler 成功被 Webhook 唤醒，并秒级处理了新消息！")
        else:
            print("❌ 第二幕失败：Scheduler 没有醒来，或者处理超时。")

    except Exception as e:
        print(f"💥 测试过程中发生严重错误: {e}")

    finally:
        print("\n🧹 [终局] 测试结束，开始打扫战场...")
        # 1. 强行掐死后台的死循环，防止终端卡死
        if 'scheduler_task' in locals() and not scheduler_task.done():
            scheduler_task.cancel()
            print("🛑 后台 Scheduler 已被强制安全关闭。")

        # 2. 清理数据库
        db.query(Notification).filter(Notification.account_id == test_account_id).delete()
        db.query(FetchAccount).filter(FetchAccount.id == test_account_id).delete()
        db.commit()
        db.close()
        print("✨ 数据库清理完毕，无痕退出！")


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_scheduler_test())