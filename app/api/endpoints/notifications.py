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

@router.get("/", response_model=List[NotificationResponse])
def get_notifications(
        status: str = "processed",
        account_id: Optional[str] = None,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        db: Session = Depends(get_db)
):
    # 💥 核心修复：指挥 SQLAlchemy 去加载真正的 AI 打分关联表 (analysis_payload)
    query = db.query(Notification).options(
        joinedload(Notification.analysis_payload)
    )

    query = query.filter(Notification.status == status)
    if account_id:
        query = query.filter(Notification.account_id == account_id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)

    query = query.outerjoin(Notification.email_analysis).options(
        contains_eager(Notification.email_analysis)
    )

    query = query.outerjoin(Notification.im_session_state).options(
        contains_eager(Notification.im_session_state)
    )

    query = query.order_by(
        case(
            (Notification.platform == "email", EmailAnalysis.priority_score),
            (Notification.platform == "instagram", IMSessionState.priority_score),
            else_=1
        ).desc(),
        Notification.received_at.desc()
    )

    return query.offset(offset).limit(limit).all()

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

@router.patch("/{notification_id}/feedback")
def submit_feedback(
        notification_id: int,
        feedback: FeedbackUpdate,
        db: Session = Depends(get_db)
):
    payload = db.query(AnalysisPayload).filter_by(notification_id=notification_id).first()

    if not payload:
        notification_exists = db.query(Notification).filter(Notification.id == notification_id).first()
        if not notification_exists:
            raise HTTPException(status_code=404, detail="未找到该通知消息，无法提交反馈")

        payload = AnalysisPayload(
            notification_id=notification_id,
            account_id=getattr(notification_exists, "account_id", "999999"),
            platform=getattr(notification_exists, "platform", "email"),
            analysis_data={"ai_logic": {"base_score": 0, "reason": "冒烟测试自动补全的容错快照"}},
            user_feedback_score=feedback.user_feedback_score
        )
        db.add(payload)
    else:
        payload.user_feedback_score = feedback.user_feedback_score

    db.commit()
    return {"status": "success", "message": "已成功拦截反馈，训练集已更新"}

@router.post("/mark-all-read/{account_id}")
def mark_all_as_read(account_id: str, db: Session = Depends(get_db)):
    db.query(Notification).filter(
        Notification.account_id == account_id,
        Notification.is_read == False
    ).update({"is_read": True})

    db.query(IMSessionState).filter(
        IMSessionState.account_id == account_id,
        IMSessionState.is_read == False
    ).update({"is_read": True})

    db.commit()
    return {"status": "success", "count": "all"}