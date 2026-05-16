# test/test_email_context_and_scorer.py
import asyncio
import sys
import os
import uuid
from datetime import datetime, timedelta

# 将项目根目录加入路径，确保能导入 app 和 workers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.account import FetchAccount
from app.models.notifications import Notification

# 💥 引入 Email 专用的 Manager 和 Scorer
from app.services.context.email.manager import get_email_formatted_context
from workers.ai.models.email.scorer import analyze_email_context

# --- 虚构的集成测试数据配置 ---
# 注意：Email 的上下文追踪强依赖于 subject 的一致性
TEST_CASES = [
    {
        "name": "极简验证码 (OTP)",
        "subject": "GitHub 登录验证",
        "messages": [
            {"sender": "GitHub", "is_from_me": False, "text": "Your authentication code is 847291.", "minutes_ago": 0},
        ]
    },
    {
        "name": "紧急报错告警",
        "subject": "🚨 [URGENT] FastAPI Backend Crash",
        "messages": [
            {"sender": "Sentry Alerts", "is_from_me": False,
             "text": "Error: 500 Internal Server Error in login component. Exception: Database connection timeout.",
             "minutes_ago": 0},
        ]
    },
    {
        "name": "常规生活通知",
        "subject": "Cykelverkstad Karlskrona - Uppdatering",
        "messages": [
            {"sender": "Bike Shop", "is_from_me": False,
             "text": "Hej! Din cykel är nu klar. Vi har fixat freehub-problemet.", "minutes_ago": 60},
        ]
    },
    {
        "name": "多轮深度技术探讨 (模拟邮件 Thread)",
        "subject": "关于 Bambu Lab 打印 PA-CF 的参数调整",
        "messages": [
            {"sender": "Gymbro", "is_from_me": False, "text": "兄弟，我用 A1 mini 打 PA-CF 老是翘边，有什么窍门吗？",
             "minutes_ago": 120},
            {"sender": "Me", "is_from_me": True,
             "text": "热床温度拉到 80度，然后记得一定要涂固体胶。如果还不行就加裙边(Brim)。", "minutes_ago": 115},
            {"sender": "Gymbro", "is_from_me": False, "text": "加了 Brim 确实好了很多！但是喷嘴好像有点堵。",
             "minutes_ago": 30},
            {"sender": "Me", "is_from_me": True, "text": "PA-CF 必须用硬化钢喷嘴啊，你换喷嘴了吗？", "minutes_ago": 15},
            {"sender": "Gymbro", "is_from_me": False,
             "text": "卧槽忘了...难怪。那我去买个喷嘴，顺便问下你的层高一般设多少？", "minutes_ago": 0},
        ]
    },
    {
        "name": "我已主动回复 (强制降权测试)",
        "subject": "MS1411 课程作业讨论",
        "messages": [
            {"sender": "Classmate", "is_from_me": False,
             "text": "第二题那个 Bayes Theorem 的推导我卡住了，能发你的过程参考下吗？", "minutes_ago": 30},
            {"sender": "Me", "is_from_me": True, "text": "没问题，我把草稿纸拍给你看，重点在先验概率的假设上。[图片附件]",
             "minutes_ago": 0},
        ]
    }
]


async def run_integration_test():
    db = SessionLocal()

    # 💥 生成测试账号的唯一标识
    test_account_id = 888888
    test_platform_id = f"test_email_{uuid.uuid4().hex[:8]}"

    print("🛠️ 初始化 Email 模块测试数据库环境...")

    try:
        # 1. 创建临时系统账号
        temp_account = FetchAccount(
            id=test_account_id,
            platform="email",
            platform_account_id=test_platform_id,
            username="test@example.com",
            config={"env": "test"}
        )
        db.add(temp_account)
        db.commit()

        print("🧪 开始 Email 完整链路集成测试 (DB -> Context Finder -> Formatter -> AI Scorer)...\n")

        for case in TEST_CASES:
            print("=" * 80)
            print(f"📡 测试用例: 【{case['name']}】 | 主题: {case['subject']}")

            # 模拟发件人邮箱
            test_external_sender_id = f"sender_{uuid.uuid4().hex[:6]}@example.com"
            now = datetime.now()

            # 2. 模拟邮件入库
            msgs_to_insert = []
            previous_msg_id = None

            for idx, msg_data in enumerate(case["messages"]):
                current_msg_id = f"email_{idx}_{uuid.uuid4().hex[:6]}"

                msg = Notification(
                    account_id=test_account_id,
                    platform="email",
                    account_msg_id=current_msg_id,
                    reply_to_mid=previous_msg_id,  # 链式挂载
                    subject=case["subject"],  # 核心：依赖主题查询
                    sender=msg_data["sender"],
                    external_sender_id=test_external_sender_id if not msg_data["is_from_me"] else "me@example.com",
                    cleaned_content=msg_data["text"],
                    is_from_me=msg_data["is_from_me"],
                    received_at=now - timedelta(minutes=msg_data["minutes_ago"]),
                    status="pending"
                )
                msgs_to_insert.append(msg)
                previous_msg_id = current_msg_id  # 为下一封邮件提供 reply_to_mid

            db.add_all(msgs_to_insert)
            db.commit()

            # 3. 激活 Context Finder & Formatter (Manager)
            # 获取数据库中该主题下最新的一封邮件
            latest_msg = db.query(Notification).filter(
                Notification.subject == case["subject"],
                Notification.account_id == test_account_id
            ).order_by(Notification.received_at.desc()).first()

            # 记录 Manager 处理耗时
            start_context_time = datetime.now()
            email_script = await get_email_formatted_context(db, latest_msg)
            context_cost = (datetime.now() - start_context_time).total_seconds()

            print(f"⏱️ Context Manager 处理耗时: {context_cost:.3f} 秒")

            # 打印格式化后的剧本，验证 Formatter 的效果
            print(f"📝 组装后的 AI 剧本预览:\n{'-' * 40}\n{email_script.strip()}\n{'-' * 40}\n")

            # 4. 激活 AI Scorer
            start_ai_time = datetime.now()
            result = await analyze_email_context(email_script)
            ai_cost = (datetime.now() - start_ai_time).total_seconds()

            if result:
                print(f"✅ AI 响应成功 (耗时: {ai_cost:.3f} 秒):")
                print(f"   🗂️ 提取分类 ID (Category ID): {result.category_id}")
                print(f"   🔥 紧急评分 (Priority): {result.priority_score}/10")
                print(f"   📝 行动摘要 (Summary): {result.summary}")
            else:
                print(f"❌ AI 响应失败或 Schema 验证不通过。")
            print("\n")

    except Exception as e:
        print(f"💥 测试过程中发生严重错误: {e}")

    finally:
        print("🧹 开始清理测试数据...")
        db.query(Notification).filter(Notification.account_id == test_account_id).delete()
        db.query(FetchAccount).filter(FetchAccount.id == test_account_id).delete()
        db.commit()
        db.close()
        print("✨ 数据库清理完毕，无痕退出！")


if __name__ == "__main__":
    asyncio.run(run_integration_test())