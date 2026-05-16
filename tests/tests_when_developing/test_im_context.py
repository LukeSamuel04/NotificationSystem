# test_context.py (单次运行测试)
import asyncio
from app.db.session import SessionLocal
from app.models.notifications import Notification
from app.services.context.manager import get_formatted_context


async def test_trigger():
    db = SessionLocal()
    # 1. 拿到最新的一条 Instagram 消息
    msg = db.query(Notification).filter(Notification.platform == "instagram").order_by(Notification.id.desc()).first()

    if msg:
        print(f"--- 正在测试消息 ID: {msg.account_msg_id} ---")
        # 2. 触发你的上下文逻辑
        script = await get_formatted_context(db, msg)
        # 3. 查看剧本
        print(script)
    else:
        print("数据库里还没消息呢，快去发一条！")
    db.close()


if __name__ == "__main__":
    asyncio.run(test_trigger())