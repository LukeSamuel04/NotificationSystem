# app/services/context/im_context_finder.py
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.notifications import Notification
from typing import List, Set
import logging

logger = logging.getLogger(__name__)


async def get_im_context(
        db: Session,
        current_msg: Notification,
        window_size: int = 10
) -> List[Notification]:
    """
    IM 上下文提取算法：
    1. 抓取当前消息前后各 window_size 条。
    2. 找出这些消息中引用的 reply_to_mid。
    3. 针对每一个引用的消息，再次抓取其前后各 window_size 条。
    4. 汇总、去重、按时间排序。
    """

    # 存储所有需要获取的消息 ID，利用 Set 自动去重
    target_ids: Set[int] = {current_msg.id}

    # 基础过滤条件：必须是同一个发送者、同一个平台
    base_filter = [
        Notification.external_sender_id == current_msg.external_sender_id,
        Notification.platform == current_msg.platform
    ]

    # --- 第一层：当前时间线扩散 ---
    # 找前面的
    prev_ids = db.query(Notification.id).filter(
        *base_filter,
        Notification.received_at < current_msg.received_at
    ).order_by(Notification.received_at.desc()).limit(window_size).all()

    # 找后面的 (通常是 Echo 消息)
    next_ids = db.query(Notification.id).filter(
        *base_filter,
        Notification.received_at > current_msg.received_at
    ).order_by(Notification.received_at.asc()).limit(window_size).all()

    # 将第一层 ID 存入 Set
    for r in (prev_ids + next_ids):
        target_ids.add(r.id)

    # --- 第二层：逻辑引用追踪 ---
    # 先把目前捞到的这些消息的 reply_to_mid 全部收集起来
    # 我们需要查询这些 ID 对应的 reply_to_mid 字段
    initial_msgs = db.query(Notification.reply_to_mid).filter(
        Notification.id.in_(target_ids),
        Notification.reply_to_mid.isnot(None)
    ).all()

    # 加上当前消息本身的引用
    anchor_mids = {m.reply_to_mid for m in initial_msgs}
    if current_msg.reply_to_mid:
        anchor_mids.add(current_msg.reply_to_mid)

    # 针对每一个引用锚点进行“二次扩散”
    if anchor_mids:
        # 找到这些被引用消息在数据库里的记录
        anchors = db.query(Notification).filter(
            Notification.account_msg_id.in_(anchor_mids),
            Notification.platform == current_msg.platform
        ).all()

        for anchor in anchors:
            target_ids.add(anchor.id)
            # 针对这个锚点，再次向前后各扩散 window_size 条
            a_prev = db.query(Notification.id).filter(
                *base_filter,
                Notification.received_at < anchor.received_at
            ).order_by(Notification.received_at.desc()).limit(window_size).all()

            a_next = db.query(Notification.id).filter(
                *base_filter,
                Notification.received_at > anchor.received_at
            ).order_by(Notification.received_at.asc()).limit(window_size).all()

            for r in (a_prev + a_next):
                target_ids.add(r.id)

    # --- 最终汇总 ---
    # 根据去重后的 ID 列表，拉取完整的 Notification 对象并按时间正序排列
    final_context = db.query(Notification).filter(
        Notification.id.in_(target_ids)
    ).order_by(Notification.received_at.asc()).all()

    logger.info(f"🔍 上下文检索完成：共找到 {len(final_context)} 条相关消息")
    return final_context