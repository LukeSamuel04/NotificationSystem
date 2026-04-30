from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
# 引入重构后的新模型
from app.models.notifications import Notification
from app.models.analysis import NotificationAnalysis
from app.schemas.notification import NotificationResponse

print('Notification endpoint is updated and active!')
router = APIRouter()


def _format_notification_response(notif: Notification, analysis_record: NotificationAnalysis):
    """
    内部辅助函数：将主表与 AI 分析表的结果拍平。
    注意：这里不再需要判断 content 还是 cleaned_content，因为主表现在只存洗干净的数据。
    """
    return {
        "id": notif.id,
        "account_id": notif.account_id,
        "account_msg_id": notif.account_msg_id,
        "sender": notif.sender,
        "subject": notif.subject,
        # 这里对应 Schema 中的 content 字段，Pydantic 会自动映射
        "cleaned_content": notif.cleaned_content,
        "status": notif.status,
        "received_at": notif.received_at,
        "created_at": notif.created_at,
        "updated_at": notif.updated_at,
        # AI 分析结果字段
        "priority_score": analysis_record.priority_score if analysis_record else None,
        "category": analysis_record.category if analysis_record else None,
        "summary": analysis_record.summary if analysis_record else None,
    }


@router.get("/unsolved", response_model=List[NotificationResponse])
def get_kanban_notifications(db: Session = Depends(get_db)):
    """获取看板上的未处理消息（高分优先）"""
    # 使用更加严谨的联表查询
    results = db.query(
        Notification,
        NotificationAnalysis
    ).outerjoin(
        NotificationAnalysis,
        Notification.id == NotificationAnalysis.notification_id
    ).filter(
        Notification.status == 'unread' # 如果你的 worker 把状态改成了 pending，这里也要对应修改
    ).order_by(
        NotificationAnalysis.priority_score.desc()
    ).all()

    return [_format_notification_response(notif, analysis_record) for notif, analysis_record in results]


@router.get("/history", response_model=List[NotificationResponse])
def get_history_notifications(db: Session = Depends(get_db)):
    """获取已归档的历史消息"""
    results = db.query(
        Notification,
        NotificationAnalysis
    ).outerjoin(
        NotificationAnalysis,
        Notification.id == NotificationAnalysis.notification_id
    ).filter(
        Notification.status == 'done'
    ).order_by(
        Notification.id.desc()
    ).all()

    return [_format_notification_response(notif, analysis_record) for notif, analysis_record in results]


@router.patch("/{notif_id}/done")
def mark_as_done(notif_id: int, db: Session = Depends(get_db)):
    """将消息标记为已处理（归档）"""
    notif = db.query(Notification).filter(Notification.id == notif_id).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.status = 'done'
    db.commit()
    return {"message": "Success", "id": notif_id}


@router.patch("/{notif_id}/restore")
def restore_notification(notif_id: int, db: Session = Depends(get_db)):
    """从历史记录中恢复消息到看板"""
    notif = db.query(Notification).filter(Notification.id == notif_id).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.status = 'unread'
    db.commit()
    return {"message": "Restored", "id": notif_id}