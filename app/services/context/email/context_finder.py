# app/services/context/email/context_finder.py
import logging
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.notifications import Notification

logger = logging.getLogger("EmailContextFinder")

class EmailContextFinder:

    @staticmethod
    def get_context_records(db: Session, current_msg: Notification, max_history: int = 5) -> list[Notification]:
        """
        无状态上下文寻回器：
        通过 Subject 和 In-Reply-To 追踪同一对话线程的历史邮件。
        返回按时间正序排列的邮件列表，列表最后一个元素必定是 current_msg。
        """
        if not current_msg:
            return []

        try:
            # 1. 广度搜索：撒网捞取同一账号下的相关历史邮件
            query = db.query(Notification).filter(
                Notification.account_id == current_msg.account_id,
                Notification.platform == 'email',
                Notification.id != current_msg.id,  # 先把当前邮件自己排除在外
                or_(
                    # 匹配 A: 主题相同 (经过了 _clean_subject 漂白后的干净主题)
                    Notification.subject == current_msg.subject,
                    # 匹配 B: 哪怕主题被改了，只要底层 ID 顺得上也算 (直系父邮件)
                    Notification.account_msg_id == current_msg.reply_to_mid
                )
            )

            # 2. 时间结界：只捞取在当前邮件“之前”发生的事情
            if current_msg.received_at:
                query = query.filter(Notification.received_at <= current_msg.received_at)

            # 3. 截断与排序：按时间倒序 (DESC) 取最近的 max_history 条
            # 这样就算这个主题聊了 100 封，我们也只取离现在最近的 5 封，保护 Token
            history_records = query.order_by(Notification.received_at.desc()).limit(max_history).all()

            # 4. 时间线重构：把拿到的最近几条历史记录翻转成“正序 (ASC)” (时间早的在前)
            history_records.reverse()

            # 5. 拼图完成：把当前正在处理的这封最新邮件，作为结局“压轴”追加到末尾
            history_records.append(current_msg)

            return history_records

        except Exception as e:
            logger.error(f"❌ 查找邮件上下文时发生异常: {e}")
            # 防御性降级：如果数据库查询崩了，不要阻塞主流程
            # 直接把当前邮件包装成单元素列表返回，让它“单兵作战”去算分
            return [current_msg]