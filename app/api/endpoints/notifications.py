# app/api/endpoints/notifications.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload, contains_eager
from sqlalchemy import func, case

from app.db.session import get_db
from app.models.notifications import Notification
from app.models.email_analysis import EmailAnalysis
from app.models.im_session import IMSessionState
from app.models.analysis_payload import AnalysisPayload
from app.schemas.notification import NotificationResponse, NotificationUpdate, FeedbackUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


# ==========================================
# 1. 核心看板列表接口 (大一统聚合器)
# ==========================================
@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
        status: str = "processed",
        account_id: Optional[str] = None,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        db: Session = Depends(get_db)
):
    # 1. 基础查询：只用 joinedload 挂载不需要用来排序的 payload
    query = db.query(Notification).options(
        joinedload(Notification.payload)
    )

    # 2. 基础过滤
    query = query.filter(Notification.status == status)
    if account_id:
        query = query.filter(Notification.account_id == account_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    # 3. 💥 核心修复：直接通过“关系属性 (Relationship)”进行 Join
    # 这样既能把数据取出来做排序，又能完美触发 contains_eager 把数据塞进对象里发给前端

    # 挂载 Email 分析数据
    query = query.outerjoin(Notification.email_analysis).options(
        contains_eager(Notification.email_analysis)
    )

    # 挂载 IM 会话数据
    query = query.outerjoin(Notification.im_session_state).options(
        contains_eager(Notification.im_session_state)
    )

    # 4. 跨表优先级综合排序
    query = query.order_by(
        case(
            (Notification.platform == "email", EmailAnalysis.priority_score),
            (Notification.platform == "instagram", IMSessionState.priority_score),
            else_=1
        ).desc(),
        Notification.received_at.desc()
    )

    return query.offset(offset).limit(limit).all()


# ==========================================
# 2. 局部更新接口 (状态流转 & 红点消除)
# ==========================================
@router.patch("/{notification_id}", response_model=NotificationResponse)
def update_notification(
        notification_id: int,
        payload: NotificationUpdate,
        db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="通知未找到")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notif, field, value)

    # 特殊联动：如果 IM 消息被标记为已读，同步更新 IM 会话状态表的红点
    if notif.platform == "instagram" and payload.is_read is True:
        session = db.query(IMSessionState).filter_by(
            external_sender_id=notif.external_sender_id,
            account_id=notif.account_id
        ).first()
        if session:
            session.is_read = True

    db.commit()
    db.refresh(notif)
    return notif


# ==========================================
# 3. 反馈飞轮接口 (人类干预算分)
# ==========================================
@router.patch("/{notification_id}/feedback")
def submit_feedback(
        notification_id: int,
        feedback: FeedbackUpdate,
        db: Session = Depends(get_db)
):
    payload = db.query(AnalysisPayload).filter_by(notification_id=notification_id).first()
    if not payload:
        raise HTTPException(status_code=404, detail="该通知暂无算法快照数据，无法提交反馈")

    payload.user_feedback_score = feedback.user_feedback_score
    db.commit()

    logger.info(f"🎯 收到用户反馈：通知 {notification_id} 被标记为 {feedback.user_feedback_score} 分")
    return {"status": "success", "message": "已成功拦截反馈，训练集已更新"}


# ==========================================
# 4. 批量已读 (用户体验增强)
# ==========================================
@router.post("/mark-all-read/{account_id}")
def mark_all_as_read(account_id: str, db: Session = Depends(get_db)):
    # 1. 更新原子消息表
    db.query(Notification).filter(
        Notification.account_id == account_id,
        Notification.is_read == False
    ).update({"is_read": True})

    # 2. 更新 IM 聚合会话表
    db.query(IMSessionState).filter(
        IMSessionState.account_id == account_id,
        IMSessionState.is_read == False
    ).update({"is_read": True})

    db.commit()
    return {"status": "success", "count": "all"}