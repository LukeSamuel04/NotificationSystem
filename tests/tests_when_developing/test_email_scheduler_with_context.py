# test/test_email_scheduler_with_context.py
import asyncio
import sys
import os
import uuid
import logging
from datetime import datetime, timedelta

# 💥 开启全局探头：将核心流转日志强制输出到控制台
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)

# 屏蔽底层三方库的通信噪音
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# 将项目根目录动态挂载至系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.account import FetchAccount
from app.models.notifications import Notification
from app.models.email_analysis import EmailAnalysis

# 导入咱们的 Email 智能包工头和门铃
from workers.ai.managers.email_scheduler import start_email_scheduler, trigger_email_scan


async def wait_for_email_processed(msg_id: int, timeout_seconds: int = 45) -> bool:
    """轮询器：每次强制开启全新数据库会话，避开事务隔离机制导致的脏读/幻读限制"""
    for _ in range(timeout_seconds):
        with SessionLocal() as check_db:
            msg = check_db.query(Notification).filter(Notification.id == msg_id).first()
            if msg and msg.status == "processed":
                return True
        await asyncio.sleep(1)
    return False


async def run_email_scheduler_test():
    # 主线程专职调度会话，仅负责铺设测试床和收尾清理
    db = SessionLocal()

    test_account_id = 999999
    test_email_address = f"test_inbox_{uuid.uuid4().hex[:6]}@bth.se"

    msg1_subject = "[URGENT] PA2552 Assignment Submission Issue"
    msg2_subject = "GitHub Actions: Run failed for repository LukeSamuel04/CZ"

    # 第三幕专用的共享主题
    thread_subject = "Re: [Architecture] Pydantic Schema Decoupling Design"

    print("🛠️ [准备阶段] 正在搭建邮件流水线自动化测试沙盒...")
    try:
        # 1. 注册兜底测试邮箱账号
        temp_account = FetchAccount(
            id=test_account_id,
            platform="email",
            platform_account_id=test_email_address,
            username="BTH Test Mailbox",
            config={"host": "imap.bth.se", "port": 993}
        )
        db.add(temp_account)
        db.commit()

        # =====================================================================
        # 🎬 第一幕：测试“冷启动自动扫盘 (单封独立邮件)”
        # =====================================================================
        print("\n🎬 [第一幕] 模拟系统从深夜维护唤醒后，捕获到单封独立积压邮件...")
        msg1 = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=f"<msg-old-{uuid.uuid4().hex[:8]}@mail.gmail.com>",
            sender="Classmate Bro",
            external_sender_id="classmate@student.bth.se",
            subject=msg1_subject,
            cleaned_content="Hi Luke,\nI am trying to push integration tests, but CI throws 500 error.\nCheck config?",
            is_from_me=False,
            received_at=datetime.now() - timedelta(hours=6),
            status="pending"
        )
        db.add(msg1)
        db.commit()
        msg1_db_id = msg1.id

        print("🚀 启动后台 Email Scheduler 守护协程...")
        scheduler_task = asyncio.create_task(start_email_scheduler())

        print("⏳ 等待第一幕独立邮件完成推理闭环...")
        success = await wait_for_email_processed(msg1_db_id)
        if success:
            print("✅ 第一幕成功：冷启动扫盘正常放行！")
        else:
            print("❌ 第一幕失败：处理超时。")

        # =====================================================================
        # 🎬 第二幕：测试“脉冲打断唤醒”
        # =====================================================================
        print("\n🎬 [第二幕] 模拟引擎挂起中，突然拉取到单封新告警...")
        msg2 = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=f"<msg-new-{uuid.uuid4().hex[:8]}@github.com>",
            sender="GitHub Notifications",
            external_sender_id="notifications@github.com",
            subject=msg2_subject,
            cleaned_content="ModuleNotFoundError: No module named 'pydantic'",
            is_from_me=False,
            received_at=datetime.now(),
            status="pending"
        )
        db.add(msg2)
        db.commit()
        msg2_db_id = msg2.id

        print("🔔 敲响门铃！触发即使解析...")
        trigger_email_scan()
        success = await wait_for_email_processed(msg2_db_id)
        if success:
            print("✅ 第二幕成功：毫秒级打断苏醒成功！")

        # =====================================================================
        # 🎬 第三幕：测试“多轮上下文聚合 (context_finder) 与批量放行”
        # =====================================================================
        print("\n🎬 [第三幕] 模拟密集的往来邮件 Thread 轰炸，实测上下文组装与防爆机制...")

        mid_a = f"<thread-a-{uuid.uuid4().hex[:6]}@bth.se>"
        mid_b = f"<thread-b-{uuid.uuid4().hex[:6]}@bth.se>"
        mid_c = f"<thread-c-{uuid.uuid4().hex[:6]}@bth.se>"

        # 1. 顶层始发邮件 (30分钟前)
        msg_a = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=mid_a,
            sender="Gymbro",
            external_sender_id="gymbro@student.bth.se",
            subject=thread_subject,
            cleaned_content="Luke, should we merge EmailConfig and UpdateConfig schemas into one to save rows?",
            is_from_me=False,
            received_at=datetime.now() - timedelta(minutes=30),
            status="pending"  # 故意设为 pending 模拟批量拉取
        )

        # 2. 我方历史回复 (15分钟前，指向 A)
        msg_b = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=mid_b,
            reply_to_mid=mid_a,  # 🔗 形成追溯链
            sender="Luke",
            subject=thread_subject,
            cleaned_content="No, keep them separated. Create needs required fields, Update needs Optionals for exclude_unset.",
            is_from_me=True,  # 👤 标记为我发出的
            received_at=datetime.now() - timedelta(minutes=15),
            status="pending"
        )

        # 3. 对方最新追问 (刚刚，指向 B)
        msg_c = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=mid_c,
            reply_to_mid=mid_b,  # 🔗 形成追溯链
            sender="Gymbro",
            external_sender_id="gymbro@student.bth.se",
            subject=thread_subject,
            cleaned_content="Ah, makes perfect sense! I'll update the router layer now. Thanks bro!",
            is_from_me=False,
            received_at=datetime.now(),
            status="pending"
        )

        # 批量入库整个 Thread
        db.add_all([msg_a, msg_b, msg_c])
        db.commit()
        msg_c_db_id = msg_c.id  # 锚定最新的一封邮件 ID

        print("🔔 再次敲响门铃，向 Executor 投喂多轮 Thread 生肉...")
        trigger_email_scan()

        print("⏳ 等待最新邮件 C 闭环，并侦测历史邮件 A 和 B 是否被连带批量放行...")
        success = await wait_for_email_processed(msg_c_db_id)

        if success:
            print("✅ 第三幕成功：多轮 Thread 已被完美闭环！")

            # 深度校验核心机制表现
            with SessionLocal() as verify_db:
                # 1. 检查批量更新表现
                status_a = verify_db.query(Notification.status).filter(Notification.account_msg_id == mid_a).scalar()
                status_b = verify_db.query(Notification.status).filter(Notification.account_msg_id == mid_b).scalar()
                print(f"   ├── 🛡️ 批量防爆核验: 邮件A状态=[{status_a}] | 邮件B状态=[{status_b}] (预期均为 processed)")

                assert status_a == "processed" and status_b == "processed", "❌ 致命错误：同 Thread 下的历史邮件未被连带放行！"

                # 2. 检查 AI 是否读懂了全链路上下文
                analysis = verify_db.query(EmailAnalysis).filter(EmailAnalysis.notification_id == msg_c_db_id).first()
                if analysis:
                    print(
                        f"   ├── 🧠 最新邮件C 挂载熟肉 -> [评分: {analysis.priority_score} | 分类ID: {analysis.category_id}]")
                    print(f"   └── 📝 全局上下文摘要快照:\n       {analysis.summary}")
                else:
                    print("   └── ❌ 错误：未能在最新邮件下找到 AI 分析产物。")
        else:
            print("❌ 第三幕失败：多轮 Thread 聚合处理超时。")

    except Exception as e:
        print(f"💥 邮件链路集成测试遭遇不可恢复性崩溃: {e}")

    finally:
        print("\n🧹 [终局] 测试使命达成，启动物理级静默回滚...")
        if 'scheduler_task' in locals() and not scheduler_task.done():
            scheduler_task.cancel()
            print("🛑 后台 Email Scheduler 监听循环已被平滑注销。")

        try:
            # 动态捞取所有测试生成的邮件 ID 并全量抹除
            msg_ids = db.query(Notification.id).filter(Notification.account_id == test_account_id).all()
            msg_id_list = [m[0] for m in msg_ids]
            if msg_id_list:
                db.query(EmailAnalysis).filter(EmailAnalysis.notification_id.in_(msg_id_list)).delete(
                    synchronize_session=False)

            db.query(Notification).filter(Notification.account_id == test_account_id).delete(synchronize_session=False)
            db.query(FetchAccount).filter(FetchAccount.id == test_account_id).delete(synchronize_session=False)
            db.commit()
            print("✨ 数据库测试床重置完毕，无脏数据泄露！")
        except Exception as cleanup_err:
            db.rollback()
            print(f"⚠️ 终局数据抹除操作出现警告: {cleanup_err}")
        finally:
            db.close()


if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_email_scheduler_test())