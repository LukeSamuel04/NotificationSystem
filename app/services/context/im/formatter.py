# app/services/context/formatter.py
from typing import List
from app.models.notifications import Notification


def format_notification_context(notifications: List[Notification]) -> str:
    """
    将消息对象列表转化为 AI 可读的对话剧本
    新增功能：精确定位被引用消息的时间点
    """
    # 💥 第一步：建立映射表
    # 使用 account_msg_id 作为 Key，方便根据回复 ID 快速检索原始消息对象
    msg_map = {m.account_msg_id: m for m in notifications if m.account_msg_id}

    lines = []

    for msg in notifications:
        # 1. 确定角色前缀
        role = "我" if msg.is_from_me else "对方"

        # 2. 格式化当前消息时间
        curr_time = msg.received_at.strftime("%Y-%m-%d %H:%M") if msg.received_at else "未知时间"

        # 3. 💥 核心改进：计算精准的回复提示词
        reply_hint = ""
        if msg.reply_to_mid:
            # 从映射表中查找被引用的那条消息
            parent_msg = msg_map.get(msg.reply_to_mid)
            if parent_msg and parent_msg.received_at:
                parent_time = parent_msg.received_at.strftime("%Y-%m-%d %H:%M")
                reply_hint = f" (回复了 {parent_time} 的一条消息)"
            else:
                # 兜底：如果被引用的消息不在本次抓取的列表内
                reply_hint = " (回复了之前的一条消息)"

        # 4. 拼装成行
        line = f"[{curr_time}] {role}{reply_hint}：{msg.cleaned_content}"
        lines.append(line)

    return "\n".join(lines)