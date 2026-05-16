# tests/tests_after_developing/8_instagram_webhook_manager.py
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# 导入关联模型，打通 SQLAlchemy 全局关系映射注册表
from app.models.analysis_payload import AnalysisPayload

# 导入待测核心业务函数与依赖模型
from app.services.instagram.webhook_manager import process_instagram_webhook
from app.models.account import FetchAccount
from app.models.notifications import Notification
from app.models.im_session import IMSessionState


class TestInstagramWebhookManager(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：动态构造一套符合 Meta 契约的标准虚拟 Webhook 载荷"""
        # 1. 创建高度内聚的 Mock 消息结构
        self.mock_message = MagicMock()
        self.mock_message.text = "Hej Luke! Please check the PA2552 Selenium test suite."
        self.mock_message.mid = "mid.instagram.message.unique_id_2026"
        self.mock_message.reply_to = None

        # 2. 组装接收与发送实体 (默认设置为：对方来信状态)
        self.mock_messaging_event = MagicMock()
        self.mock_messaging_event.message = self.mock_message
        self.mock_messaging_event.sender.id = "external_user_id_888"
        self.mock_messaging_event.recipient.id = "my_page_meta_id_999"
        self.mock_messaging_event.timestamp = 1715787600000  # 对应 2026 年某时间戳

        # 3. 装配顶层 Payload
        self.mock_entry = MagicMock()
        self.mock_entry.id = "my_page_meta_id_999"
        self.mock_entry.messaging = [self.mock_messaging_event]

        self.mock_payload = MagicMock()
        self.mock_payload.entry = [self.mock_entry]

        # 4. 模拟一个系统已绑定的健康基础账号
        self.mock_account = MagicMock(spec=FetchAccount)
        self.mock_account.id = 10
        self.mock_account.platform_account_id = "my_page_meta_id_999"
        self.mock_account.platform = "instagram"

    async def test_process_webhook_incoming_from_partner(self):
        """【测试 1】验证对方来信：Partner ID 正确映射为发送者，成功触发历史唤醒，并点亮未读红点"""
        mock_db = MagicMock(spec=Session)

        # 模拟数据库查询：第一步先查出对应的绑定账号
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = self.mock_account

        # 执行分拣核心（is_from_me = False，代表对方发来的新消息）
        await process_instagram_webhook(mock_db, self.mock_payload, is_from_me=False)

        # 核心断言与行为追溯：
        mock_db.add.assert_called_once()
        inserted_notification = mock_db.add.call_args[0][0]
        self.assertIsInstance(inserted_notification, Notification)

        # 对方来信时，对话伙伴（external_sender_id）必须是真实客户的 sender.id
        self.assertEqual(inserted_notification.external_sender_id, "external_user_id_888")
        self.assertEqual(inserted_notification.sender, "IG User")

        # 验证全局会话唤醒与红点唤醒（执行了 2 次查询更新）
        self.assertEqual(mock_db.query.return_value.filter.return_value.update.call_count, 2)
        mock_db.commit.assert_called_once()
        mock_db.rollback.assert_not_called()

    async def test_process_webhook_echo_from_me(self):
        """【测试 2】验证我方回复（回声消息）：Partner ID 动态纠正为接收者，触发历史唤醒，但严禁点亮未读红点"""
        mock_db = MagicMock(spec=Session)
        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = self.mock_account

        # 💥 核心修复：对齐 Meta 官方 Echo 契约，颠倒发送者与接收者的 ID 状态
        # 既然是我回的消息，发送者(sender)必然是我，接收者(recipient)必然是外部客户
        self.mock_messaging_event.sender.id = "my_page_meta_id_999"
        self.mock_messaging_event.recipient.id = "external_user_id_888"

        # 执行分拣核心（is_from_me = True，代表我们在手机端做出了回复，Meta 推送了 Echo）
        await process_instagram_webhook(mock_db, self.mock_payload, is_from_me=True)

        # 核心断言与行为追溯：
        mock_db.add.assert_called_once()
        inserted_notification = mock_db.add.call_args[0][0]

        # 💥 契约对齐断言：即使我方发信，对话伙伴（external_sender_id）依然能够被动态清洗并锁死为客户 ID
        self.assertEqual(inserted_notification.external_sender_id, "external_user_id_888")
        self.assertEqual(inserted_notification.sender, "Me")

        # 关键策略断言：我方发的消息绝不能给自己点亮未读红点！（只执行 1 次已归档消息激活）
        self.assertEqual(mock_db.query.return_value.filter.return_value.update.call_count, 1)
        mock_db.commit.assert_called_once()

    async def test_process_webhook_database_crash_rollback(self):
        """【测试 3】验证容错鲁棒性：当数据库在执行期间发生未知崩溃时，事务必须自动 Rollback 阻绝脏数据"""
        mock_db = MagicMock(spec=Session)
        mock_db.commit.side_effect = Exception("Navicat Connection Pool Broken or Deadlock detected")

        mock_query = mock_db.query.return_value.filter.return_value
        mock_query.first.return_value = self.mock_account

        # 执行动作
        await process_instagram_webhook(mock_db, self.mock_payload, is_from_me=False)

        # 断言判定：必须自动执行 rollback 回滚
        mock_db.rollback.assert_called_once()


# 💥 挂载标准单元测试启动飞轮，允许直接一键点击运行
if __name__ == "__main__":
    unittest.main()