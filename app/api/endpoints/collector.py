from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
# 注意：这里增加导入了 SessionLocal，用于后台独立线程的数据库连接
from app.db.session import get_db, SessionLocal
from app.models.notification import Notification
from app.schemas.email import EmailCreate, Email
from app.services import processor
from sqlalchemy import desc

router = APIRouter()


# ==========================================
# 核心 Worker：后台 AI 处理逻辑
# ==========================================
def process_notification_task(notif_id: int):
    """
    后台任务处理函数。
    由 BackgroundTasks 触发，运行在独立线程中，绝不阻塞主程序的网络响应。
    """
    # 必须在后台线程中开启一个全新的数据库会话
    db = SessionLocal()
    try:
        # 1. 捞取刚刚存入的 pending 状态的邮件
        notif = db.query(Notification).filter(Notification.id == notif_id).first()
        if not notif:
            print(f"⚠️ 找不到 ID 为 {notif_id} 的邮件记录")
            return

        print(f"⚙️ 正在后台处理邮件 ID {notif_id}...")

        # 2. 调用 AI 引擎执行耗时的打分任务
        priority_score, category = processor.analyze_email_priority(
            subject=notif.subject,
            content=notif.raw_content
        )

        # 3. 更新数据库：填充分数，并将状态扭转为 "unread" (等待前端展示)
        notif.priority_score = priority_score
        notif.category = category
        notif.status = "unread"
        db.commit()

        print(f"✅ AI 分析完成：ID {notif_id}，得分 {priority_score}")

    except Exception as e:
        print(f"❌ 后台 AI 分析失败：{e}")
        # 如果崩溃，状态仍保留为 pending，保证数据不丢失，可用于日后排查
    finally:
        # 无论成功失败，务必关闭独立的数据库会话，防止连接池泄漏
        db.close()


# ==========================================
# 路由 1：自动化邮件监听入口 (异步防阻塞)
# ==========================================
@router.post("/collect/auto", response_model=Email)
async def collect_email_auto(
        email_in: EmailCreate,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    """
    供 email_listener.py 专用的自动化接口。
    职责：光速接收数据，存为 pending，并派发后台任务，立刻响应 200 OK。
    """
    email_data = email_in.model_dump()

    # 赋予初始占位状态，防止前端渲染出错
    email_data.update({
        "priority_score": 0.0,
        "category": "analyzing",
        "status": "pending"
    })

    # 瞬间入库
    db_notif = Notification(**email_data)
    db.add(db_notif)
    db.commit()
    db.refresh(db_notif)

    # 核心：将耗时的 AI 算分任务扔给 FastAPI 的后台队列
    background_tasks.add_task(process_notification_task, db_notif.id)

    # 立刻返回，让 Listener 无缝去抓取下一封邮件
    return db_notif


# ==========================================
# 路由 2：前端手动录入入口 (同步即时响应)
# ==========================================
@router.post("/collect", response_model=Email)
def collect_email_manual(
        email_in: EmailCreate,
        db: Session = Depends(get_db)
):
    """
    供 React 前端手动输入的接口。
    职责：同步等待 AI 处理完毕，以便前端立刻看到最终分数。
    """
    print(">>>>>> 收到前端发送的手动录入请求 <<<<<<")
    email_data = email_in.model_dump()

    try:
        priority_score, category = processor.analyze_email_priority(
            subject=email_in.subject,
            content=email_in.raw_content
        )
    except Exception as e:
        print(f"AI 引擎临时罢工: {e}")
        priority_score, category = 5.0, "general"

    email_data.update({
        "priority_score": priority_score,
        "category": category,
        "status": "unread"
    })

    db_email = Notification(**email_data)
    db.add(db_email)
    db.commit()
    db.refresh(db_email)
    return db_email


# ==========================================
# 路由 3：前端看板数据拉取
# ==========================================
@router.get("/notifications", response_model=List[Email])
def get_notifications(
        skip: int = 0,
        limit: int = 100,
        db: Session = Depends(get_db)
):
    """
    获取通知列表，供 React 看板展示使用。
    核心逻辑：排除状态为 "done" 的任务，并按 priority_score 从高到低排序，确保最紧急的任务置顶。
    """
    print(">>>>>> 前端正在拉取通知列表 (已过滤完成项) <<<<<<")
    notifications = (
        db.query(Notification)
        .filter(Notification.status != "done")  # 核心拦截：不再向前端输送已完成的数据
        .order_by(Notification.priority_score.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return notifications


# ==========================================
# 路由 4：状态扭转 (完成任务)
# ==========================================
@router.patch("/{notif_id}/done")
def mark_notification_as_done(
        notif_id: int,
        db: Session = Depends(get_db)
):
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        from fastapi import HTTPException  # 确保顶部引了 HTTPException
        raise HTTPException(status_code=404, detail="任务不存在")

    notif.status = "done"
    db.commit()

    return {"message": "✅ 任务已完成", "id": notif_id}


# 注意：如果你的文件顶部还没有导入 desc，需要加上：
# from sqlalchemy import desc

# ==========================================
# 5. 历史记录拉取接口 (MVP 版：全量拉取 + 倒序)
# ==========================================
@router.get("/history")
def get_notification_history(db: Session = Depends(get_db)):
    """
    拉取所有已完成的任务，并按时间（ID）倒序排列。
    """
    history_items = (
        db.query(Notification)
        .filter(Notification.status == "done")
        # 使用 id.desc() 相当于按入库时间倒序，最新的任务排在最前面
        .order_by(Notification.id.desc())
        .all()
    )
    return history_items


# ==========================================
# 6. 任务反悔/恢复接口
# ==========================================
@router.patch("/{notif_id}/restore")
def restore_notification(
        notif_id: int,
        db: Session = Depends(get_db)
):
    """
    将已完成的任务重新打回未读状态，让它回到看板。
    """
    notif = db.query(Notification).filter(Notification.id == notif_id).first()

    if not notif:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="任务不存在")

    # 核心动作：把状态改回 unread (对应看板的查询条件)
    notif.status = "unread"
    db.commit()

    return {"message": "🔄 任务已恢复为待办", "id": notif_id}