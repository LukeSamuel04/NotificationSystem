# test/test_email_context.py
import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta

# 将项目根目录加入路径，确保能导入 app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.account import FetchAccount
from app.models.notifications import Notification

# 💥 引入 Email 专用的 Manager (它内部封装了 ContextFinder 和 Formatter)
from app.services.context.email.manager import get_email_formatted_context


async def test_deep_email_context():
    db = SessionLocal()

    # 生成测试用的唯一 ID
    test_account_id = 777777
    test_platform_id = f"test_ctx_{uuid.uuid4().hex[:8]}"
    test_external_sender = "teammate@example.com"
    test_subject = "Re: 服务器 Redis 内存泄漏排查"

    print("🛠️ 初始化 Context 深度追踪测试环境...")

    try:
        # 1. 挂载测试账号
        temp_account = FetchAccount(
            id=test_account_id,
            platform="email",
            platform_account_id=test_platform_id,
            username="my_test_email@example.com",
            config={"env": "test"}
        )
        db.add(temp_account)
        db.commit()

        # 2. 构造较深层数的连环邮件对话 (6 层)
        # 注意：时间顺序是从旧到新
        thread_messages = [
            {"sender": "Teammate", "is_from_me": False,
             "text": "嘿，昨天上线的那个版本，Redis 内存一直在飙升，你注意到了吗？", "minutes_ago": 120},
            {"sender": "Me", "is_from_me": True, "text": "看到了，我在看监控。好像是那个处理 Webhook 的队列没消费完？",
             "minutes_ago": 100},
            {"sender": "Teammate", "is_from_me": False,
             "text": "我刚看了日志，队列是空的，但连接数爆了。是不是连接池没释放？", "minutes_ago": 80},
            {"sender": "Me", "is_from_me": True,
             "text": "有道理！你把 celery 的 worker 并发数调低一点试试，顺便查一下有没有僵尸进程。", "minutes_ago": 60},
            {"sender": "Teammate", "is_from_me": False,
             "text": "好，我刚把并发降到了 4，并且重启了 Redis 实例。内存掉下来了！", "minutes_ago": 30},
            # 👇 这是最新的一封待处理邮件
            {"sender": "Teammate", "is_from_me": False,
             "text": "不过根本原因还没找到，你下午有空一起 review 一下 Redis 的连接池配置代码吗？", "minutes_ago": 0},
        ]

        print(f"📦 正在入库 {len(thread_messages)} 封具有层级关系的邮件...")

        msgs_to_insert = []
        previous_msg_id = None
        now = datetime.now()

        for idx, msg_data in enumerate(thread_messages):
            current_msg_id = f"ctx_email_{idx}_{uuid.uuid4().hex[:6]}"

            msg = Notification(
                account_id=test_account_id,
                platform="email",
                account_msg_id=current_msg_id,
                reply_to_mid=previous_msg_id,  # 👈 极其关键：模拟真实的邮件回复链
                subject=test_subject,  # 👈 极其关键：模拟主题一致性
                sender=msg_data["sender"],
                external_sender_id=test_external_sender if not msg_data["is_from_me"] else "my_test_email@example.com",
                cleaned_content=msg_data["text"],
                is_from_me=msg_data["is_from_me"],
                received_at=now - timedelta(minutes=msg_data["minutes_ago"]),
                status="pending"
            )
            msgs_to_insert.append(msg)
            previous_msg_id = current_msg_id  # 铁索连环

        db.add_all(msgs_to_insert)
        db.commit()

        # 3. 抓取最新的一封邮件
        latest_msg = db.query(Notification).filter(
            Notification.subject == test_subject,
            Notification.account_id == test_account_id
        ).order_by(Notification.received_at.desc()).first()

        print(f"\n🎯 锁定最新邮件 ID: {latest_msg.account_msg_id}")
        print("🕵️‍♂️ 触发 Context Finder 开始顺藤摸瓜...\n")

        # 4. 执行获取上下文的核心逻辑
        start_time = datetime.now()
        script = await get_email_formatted_context(db, latest_msg)
        cost_time = (datetime.now() - start_time).total_seconds()

        print("=" * 60)
        print(f"🎬 最终生成的 AI 剧本 (耗时 {cost_time:.3f} 秒):")
        print("=" * 60)
        print(script)
        print("=" * 60)

    except Exception as e:
        print(f"💥 测试过程中发生错误: {e}")

    finally:
        print("\n🧹 开始清洗数据库...")
        # 清除当前测试账号关联的所有通知
        db.query(Notification).filter(Notification.account_id == test_account_id).delete()
        # 清除测试账号
        db.query(FetchAccount).filter(FetchAccount.id == test_account_id).delete()
        db.commit()
        db.close()
        print("✨ 数据库清洗完毕，未留下任何痕迹！")


if __name__ == "__main__":
    asyncio.run(test_deep_email_context())