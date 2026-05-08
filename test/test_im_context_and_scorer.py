# test/test_im_context_and_scorer.py
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

from app.services.context.manager import get_formatted_context
from workers.ai.models.social_media.scorer import analyze_social_media_session

# --- 虚构的集成测试数据配置 ---
TEST_CASES = [
    {
        "name": "日常闲聊",
        "messages": [
            {"sender": "IG User", "is_from_me": False, "text": "哈哈，你看到那个猫片了吗？太逗了。", "minutes_ago": 5},
            {"sender": "IG User", "is_from_me": False, "text": "[视频附件]", "minutes_ago": 0},
        ]
    },
    {
        "name": "技术求救",
        "messages": [
            {"sender": "IG User", "is_from_me": False,
             "text": "那个...你上次说的那个 FastAPI 的跨域配置，能发我一份代码参考吗？", "minutes_ago": 2},
            {"sender": "IG User", "is_from_me": False, "text": "我这边一直报 403 错误，急着上线，求救求救！",
             "minutes_ago": 0},
        ]
    },
    {
        "name": "多话题场景",
        "messages": [
            {"sender": "IG User", "is_from_me": False, "text": "兄弟，今天晚上 Karlskrona 那家火锅去不去？",
             "minutes_ago": 1},
            {"sender": "IG User", "is_from_me": False,
             "text": "另外，我 3D 打印机的切片设置好像有点问题，底层粘不住，你帮我看看参数？", "minutes_ago": 0},
        ]
    },
    {
        "name": "已回复场景",
        "messages": [
            {"sender": "IG User", "is_from_me": False, "text": "你什么时候有空帮我修一下电脑？", "minutes_ago": 10},
            {"sender": "Me", "is_from_me": True, "text": "晚上八点以后吧，我现在的课还没上完。", "minutes_ago": 0},
        ]
    },
    {
        "name": "🔥 极限深水区 (3天跨度/30+消息/话题漂移/突发危机) 🔥",
        "messages": [
            # --- 第一天：两天前 (约 2880 分钟前) - 干扰项 ---
            {"sender": "IG User", "is_from_me": False, "text": "兄弟，上次你说的那个PETG-GF耗材我买了。",
             "minutes_ago": 2880},
            {"sender": "IG User", "is_from_me": False, "text": "打印温度你一般设置多少？", "minutes_ago": 2878},
            {"sender": "Me", "is_from_me": True, "text": "我一般用260度，热床80度。", "minutes_ago": 2870},
            {"sender": "IG User", "is_from_me": False, "text": "好嘞，我试试。", "minutes_ago": 2865},
            {"sender": "IG User", "is_from_me": False, "text": "感觉有点拉丝啊。", "minutes_ago": 2800},
            {"sender": "Me", "is_from_me": True, "text": "回抽调高一点，风扇开大点试试。", "minutes_ago": 2795},
            {"sender": "IG User", "is_from_me": False, "text": "调了回抽长度到2mm，好多了。", "minutes_ago": 2780},
            {"sender": "IG User", "is_from_me": False, "text": "牛逼，打出来强度确实可以！", "minutes_ago": 2770},
            {"sender": "Me", "is_from_me": True, "text": "那是，加了玻纤的肯定硬。", "minutes_ago": 2760},
            {"sender": "IG User", "is_from_me": False, "text": "等我把这个外壳打完发你看看。", "minutes_ago": 2750},

            # --- 第二天：昨天 (约 1440 分钟前) - 过渡项 ---
            {"sender": "IG User", "is_from_me": False, "text": "[图片] 看看这个外壳质感。", "minutes_ago": 1440},
            {"sender": "Me", "is_from_me": True, "text": "帅啊！严丝合缝。", "minutes_ago": 1435},
            {"sender": "IG User", "is_from_me": False, "text": "哈哈，就是废喷嘴。换了个硬化钢的。", "minutes_ago": 1430},
            {"sender": "IG User", "is_from_me": False, "text": "对了，你最近那个通知系统搞得咋样了？",
             "minutes_ago": 1420},
            {"sender": "Me", "is_from_me": True, "text": "还在调 AI 算分那块，昨天踩了个坑。", "minutes_ago": 1410},
            {"sender": "IG User", "is_from_me": False, "text": "加油加油，搞完了让我白嫖一下代码。", "minutes_ago": 1400},
            {"sender": "Me", "is_from_me": True, "text": "没问题，到时候发你 Github 链接。", "minutes_ago": 1390},

            # --- 第三天：刚才 (60分钟内) - 💥 真正的高优诉求 💥 ---
            {"sender": "IG User", "is_from_me": False, "text": "在吗？救急求救！", "minutes_ago": 45},
            {"sender": "IG User", "is_from_me": False, "text": "我这边的服务器好像挂了。", "minutes_ago": 44},
            {"sender": "Me", "is_from_me": True, "text": "咋了？什么报错？", "minutes_ago": 40},
            {"sender": "IG User", "is_from_me": False, "text": "连不上数据库了，报 Connection refused。",
             "minutes_ago": 38},
            {"sender": "IG User", "is_from_me": False, "text": "我查了下好像是连接池爆了。", "minutes_ago": 35},
            {"sender": "Me", "is_from_me": True, "text": "你用的 SQLAlchemy 吗？把 pool_size 调大点试试。",
             "minutes_ago": 30},
            {"sender": "IG User", "is_from_me": False, "text": "我加了，但是好像重启后立马又满了。", "minutes_ago": 25},
            {"sender": "IG User", "is_from_me": False, "text": "是不是哪里有死循环没关 session 啊？", "minutes_ago": 20},
            {"sender": "IG User", "is_from_me": False, "text": "你方便帮我 review 一下这几段代码吗？",
             "minutes_ago": 10},
            {"sender": "IG User", "is_from_me": False, "text": "我客户那边急着要看演示，马上要开会了！",
             "minutes_ago": 5},
            {"sender": "IG User", "is_from_me": False, "text": "兄弟在线等，急急急！！！", "minutes_ago": 0},
        ]
    }
]


async def run_integration_test():
    db = SessionLocal()

    # 💥 生成测试账号的唯一标识
    test_account_id = 999999
    test_platform_id = f"test_ig_{uuid.uuid4().hex[:8]}"

    print("🛠️ 初始化测试数据库环境...")

    try:
        # 1. 创建临时系统账号
        temp_account = FetchAccount(
            id=test_account_id,
            platform="instagram",
            platform_account_id=test_platform_id,
            username="Integration Test Account",
            config={"env": "test", "token": "dummy"}
        )
        db.add(temp_account)
        db.commit()

        print("🧪 开始 IM 完整链路集成测试 (DB -> Context -> AI)...\n")

        for case in TEST_CASES:
            print("=" * 70)
            print(f"📡 测试用例: 【{case['name']}】")

            # 为每个测试用例创建一个独立的外部发件人 ID
            test_external_sender_id = f"test_user_{uuid.uuid4().hex[:8]}"
            now = datetime.now()

            # 2. 模拟消息入库
            msgs_to_insert = []
            for idx, msg_data in enumerate(case["messages"]):
                msg = Notification(
                    account_id=test_account_id,
                    platform="instagram",
                    account_msg_id=f"msg_{idx}_{uuid.uuid4().hex[:4]}",
                    sender=msg_data["sender"],
                    external_sender_id=test_external_sender_id,
                    cleaned_content=msg_data["text"],
                    is_from_me=msg_data["is_from_me"],
                    received_at=now - timedelta(minutes=msg_data["minutes_ago"]),
                    status="pending"
                )
                msgs_to_insert.append(msg)

            db.add_all(msgs_to_insert)
            db.commit()

            # 3. 激活 Context Finder
            latest_msg = db.query(Notification).filter(
                Notification.external_sender_id == test_external_sender_id,
                Notification.account_id == test_account_id
            ).order_by(Notification.received_at.desc()).first()

            # 记录 Context 提取耗时
            start_context_time = datetime.now()
            chat_context_script = await get_formatted_context(db, latest_msg)
            context_cost = (datetime.now() - start_context_time).total_seconds()

            print(f"⏱️ Context Finder 提取耗时: {context_cost:.3f} 秒")
            print(f"📏 剧本长度: 共 {len(case['messages'])} 条消息，文本长度 {len(chat_context_script)} 字符")

            if len(case['messages']) > 10:
                print("📝 剧本预览 (由于过长，仅展示头尾):")
                lines = chat_context_script.strip().split('\n')
                print('\n'.join(lines[:3]) + "\n......\n......\n" + '\n'.join(lines[-4:]) + "\n")
            else:
                print(f"📝 剧本预览:\n{chat_context_script.strip()}\n")

            # 4. 激活 AI Scorer
            start_ai_time = datetime.now()
            result = await analyze_social_media_session(chat_context_script)
            ai_cost = (datetime.now() - start_ai_time).total_seconds()

            if result:
                print(f"✅ AI 响应成功 (耗时: {ai_cost:.3f} 秒):")
                print(f"   🔹 提取话题: {result.current_topic}")
                print(f"   🔹 紧急评分: {result.priority_score}/10")
                print(f"   🔹 浓缩摘要: {result.summary_snapshot}")
            else:
                print(f"❌ AI 响应失败或解析错误。")
            print("\n")

    except Exception as e:
        print(f"💥 测试过程中发生严重错误: {e}")

    finally:
        print("🧹 开始清理测试数据...")
        # 彻底清空本次测试产生的所有虚拟数据
        db.query(Notification).filter(Notification.account_id == test_account_id).delete()
        db.query(FetchAccount).filter(FetchAccount.id == test_account_id).delete()
        db.commit()
        db.close()
        print("✨ 数据库清理完毕，无痕退出！")


if __name__ == "__main__":
    asyncio.run(run_integration_test())