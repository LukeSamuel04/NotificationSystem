# test/test_email_scheduler.py
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
from app.models.email_analysis import EmailAnalysis  # 引入分析表以便深度校验 AI 产出结果

# 导入咱们的 Email 智能包工头和门铃
from workers.ai.managers.email_scheduler import start_email_scheduler, trigger_email_scan


async def wait_for_email_processed(msg_id: int, timeout_seconds: int = 45) -> bool:
    """
    动态轮询器（邮件专用版）：
    邮件 AI 算分耗时通常长于简短的 IM 消息，故将超时上限略微调高至 45 秒。
    每次强制开启全新数据库会话，避开事务隔离机制导致的脏读/幻读限制。
    """
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

    # 模拟真实场景下的连续邮件实体
    msg1_subject = "[URGENT] PA2552 Assignment Submission Issue"
    msg2_subject = "GitHub Actions: Run failed for repository LukeSamuel04/CZ"

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
        # 🎬 第一幕：测试“冷启动自动扫盘 (清理历史积压 Thread)”
        # =====================================================================
        print("\n🎬 [第一幕] 模拟系统从深夜维护唤醒后，捕获到收件箱积压的未读邮件...")

        # 逼真数据构造：模拟学生遭遇作业提交故障发来的长文求助
        msg1_content = (
            "Hi Luke,\n\n"
            "I am trying to push my integration tests for the priority message queue system, "
            "but the CI pipeline is throwing a 500 server error on authentication.\n"
            "Could you check the OAuth payload config?\n\n"
            "Best regards,\nClassmate Bro\n--\nBlekinge Institute of Technology"
        )

        msg1 = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=f"<msg-old-{uuid.uuid4().hex[:8]}@mail.gmail.com>",
            sender="Classmate Bro",
            external_sender_id="classmate@student.bth.se",
            subject=msg1_subject,
            cleaned_content=msg1_content,
            is_from_me=False,
            received_at=datetime.now() - timedelta(hours=6),
            status="pending"
        )
        db.add(msg1)
        db.commit()

        # 记录下自增生成的主键 ID，用于精确溯源
        msg1_db_id = msg1.id

        print("🚀 启动后台 Email Scheduler 守护协程...")
        scheduler_task = asyncio.create_task(start_email_scheduler())

        print("⏳ 监听引擎运转，等待初始积压邮件完成 LLM 推理闭环...")
        success = await wait_for_email_processed(msg1_db_id)

        if success:
            print("✅ 第一幕成功：Scheduler 启动即执行深度扫盘，完美释放了阻塞的邮件队列！")
            # 顺手深度抽查 AI 算分流水线是否正常输出
            with SessionLocal() as verify_db:
                analysis = verify_db.query(EmailAnalysis).filter(EmailAnalysis.notification_id == msg1_db_id).first()
                if analysis:
                    print(
                        f"   └── 🧠 联动验证通过：AI 成功挂载分析插槽 -> [评分: {analysis.priority_score} | 分类ID: {analysis.category_id}]")
                    print(f"   └── 📝 浓缩摘要快照: {analysis.summary}")
                else:
                    print("   └── ⚠️ 警告：邮件主表状态已放行，但 AI 分析记录未能在子表中找到对应快照。")
        else:
            print("❌ 第一幕失败：历史邮件队列未被成功闭环，或模型调用耗时超出阈值。")

        # =====================================================================
        # 🎬 第二幕：测试“收件模块落盘瞬间触发脉冲唤醒”
        # =====================================================================
        print("\n🎬 [第二幕] 模拟引擎平稳挂起中，底层 IMAP IDLE 服务突然拉取到新告警...")

        msg2_content = (
            "Error summary:\n"
            "Process completed with exit code 1.\n"
            "ModuleNotFoundError: No module named 'pydantic'\n"
            "View workflow run details at github.com/LukeSamuel04/CZ/actions"
        )

        msg2 = Notification(
            account_id=test_account_id,
            platform="email",
            account_msg_id=f"<msg-new-{uuid.uuid4().hex[:8]}@github.com>",
            sender="GitHub Notifications",
            external_sender_id="notifications@github.com",
            subject=msg2_subject,
            cleaned_content=msg2_content,
            is_from_me=False,
            received_at=datetime.now(),
            status="pending"
        )
        db.add(msg2)
        db.commit()
        msg2_db_id = msg2.id

        print("🔔 叮咚！底层收件脚本落盘成功，高频敲响调度器门铃！")
        trigger_email_scan()

        print("⏳ 观测数据库状态变更，确认系统是否具备毫秒级打断休眠能力...")
        success = await wait_for_email_processed(msg2_db_id)

        if success:
            print("✅ 第二幕成功：Scheduler 成功截获事件触发信号，即时唤醒 AI 执行器消化了最新来信！")
        else:
            print("❌ 第二幕失败：事件唤醒脉冲未能打断 30 秒休眠，或流水线执行异常。")

    except Exception as e:
        print(f"💥 邮件链路集成测试遭遇不可恢复性崩溃: {e}")

    finally:
        print("\n🧹 [终局] 测试使命达成，启动物理级静默回滚...")

        # 1. 强行切断长驻内存的轮询死循环
        if 'scheduler_task' in locals() and not scheduler_task.done():
            scheduler_task.cancel()
            print("🛑 后台 Email Scheduler 监听循环已被平滑注销。")

        # 2. 干净剔除级联产生的脏数据
        try:
            # 优先抹除挂载在邮件实体下的 AI 分析子表数据
            msg_ids = db.query(Notification.id).filter(Notification.account_id == test_account_id).all()
            msg_id_list = [m[0] for m in msg_ids]
            if msg_id_list:
                db.query(EmailAnalysis).filter(EmailAnalysis.notification_id.in_(msg_id_list)).delete(
                    synchronize_session=False)

            # 抹除核心通知表记录
            db.query(Notification).filter(Notification.account_id == test_account_id).delete(synchronize_session=False)

            # 抹除系统测试账号
            db.query(FetchAccount).filter(FetchAccount.id == test_account_id).delete(synchronize_session=False)

            db.commit()
            print("✨ 数据库测试床重置完毕，无脏数据泄露！")
        except Exception as cleanup_err:
            db.rollback()
            print(f"⚠️ 终局数据抹除操作出现警告: {cleanup_err}")
        finally:
            db.close()


if __name__ == "__main__":
    # 规避 Windows 环境下标准 Asyncio 事件循环关闭时引发的 RuntimeError 异常
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_email_scheduler_test())