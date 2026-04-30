# app/services/ai/score_manager.py
from sqlalchemy.orm import Session

# 导入新的模型
from app.models.notifications import Notification
from app.models.analysis import NotificationAnalysis

# 导入 AI 大脑
from app.services.ai.score import analyze_email_priority

def process_pending_notifications(db: Session, batch_size: int = 50):
    """
    扫描待处理的干净数据，调用 AI 算分，并存入分析表
    :param db: 数据库会话
    :param batch_size: 每次处理的最大条数
    """
    # 1. 捞取数据：找 status 为 'pending' 的主表记录
    pending_msgs = db.query(Notification) \
        .filter(Notification.status == "pending") \
        .limit(batch_size) \
        .all()

    if not pending_msgs:
        print("📭 暂无需要 AI 处理的新消息。")
        return 0

    print(f"⚙️ 捞取到 {len(pending_msgs)} 条待处理消息，开始 AI 算分...")
    processed_count = 0

    for msg in pending_msgs:
        print(f"  -> 正在处理消息 ID: {msg.id} | 标题: {msg.subject}")

        try:
            # 2. 安全获取标题和纯文本内容，防范 None 值
            safe_subject = msg.subject or ""
            safe_content = msg.cleaned_content or ""

            # 3. AI 算分：同时将标题和内容作为两个参数传入
            ai_result = analyze_email_priority(subject=safe_subject, content=safe_content)

            if ai_result:
                # 4. 组装分析表对象 (写进 notification_analysis 表)
                analysis_record = NotificationAnalysis(
                    notification_id=msg.id,
                    priority_score=ai_result.get("priority_score"),
                    category=ai_result.get("category"),
                    summary=ai_result.get("summary")
                )
                db.add(analysis_record)

                # 5. 标记主表为 unread，瞬间推送到前端看板
                msg.status = "unread"
                processed_count += 1
            else:
                print(f"⚠️ 消息 {msg.id} AI 分析未返回有效结果")
                msg.status = "error"

        except Exception as e:
            print(f"❌ 处理消息 ID {msg.id} 时发生错误: {e}")
            msg.status = "error"

    # 6. 统一提交到数据库
    try:
        db.commit()
        print(f"✅ 成功完成 {processed_count} 条消息的 AI 算分并入库！")
    except Exception as e:
        db.rollback()
        print(f"💥 数据库保存失败，已回滚: {e}")
        return 0

    return processed_count