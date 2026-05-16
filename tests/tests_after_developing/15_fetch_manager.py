# tests/tests_after_developing/15_test_fetch_manager.py
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.notification.fetch_manager import (
    process_and_save_message,
    fetch_messages_for_account,
    fetch_loop
)
from app.models.account import FetchAccount


class TestFetchManager(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备"""
        self.mock_db = MagicMock()

        # 构造一个模拟的 Email 账号
        self.mock_account = MagicMock(spec=FetchAccount)
        self.mock_account.id = 101
        self.mock_account.platform = "email"
        self.mock_account.username = "test_luke@bth.se"
        self.mock_account.config = {"host": "imap.bth.se", "password": "mock_password"}

        # 构造一条模拟抓取到的新邮件数据
        self.raw_message_data = {
            "account_msg_id": "email_mid_2026",
            "reply_to_mid": "email_parent_mid",
            "sender": "professor@bth.se",
            "subject": "PA2552 Exam Results",
            "content": "<p>You passed the exam.</p>",
            "is_from_me": False,
            "received_at": datetime.now()
        }

    @patch("workers.notification.fetch_manager.clean_html")
    def test_process_and_save_message_success(self, mock_clean_html):
        """【测试 1】消息入库引擎验证：验证重复去重、HTML清洗、Notification 与 Payload 双表落盘的完整性"""

        # 1. 模拟去重机制：数据库中找不到该消息，代表是新消息
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        # 2. 模拟 HTML 清洗器的工作
        mock_clean_html.return_value = "You passed the exam."

        # 3. 触发核心入库函数
        result = process_and_save_message(self.mock_db, self.mock_account, self.raw_message_data)

        # 4. 强力断言：
        self.assertIsNotNone(result)
        self.assertEqual(result.cleaned_content, "You passed the exam.")
        self.assertEqual(result.status, "pending")  # 对方发来的新邮件状态必须是 pending

        # 验证双写事务：必须向 DB 中 add 两次（一次基础表，一次 Payload 源数据表）
        self.assertEqual(self.mock_db.add.call_count, 2)
        self.mock_db.commit.assert_called_once()
        self.mock_db.rollback.assert_not_called()

    @patch("workers.notification.fetch_manager.EmailFetcher")
    @patch("workers.notification.fetch_manager.asyncio.sleep", new_callable=AsyncMock)
    async def test_fetch_messages_for_account_workflow(self, mock_sleep, mock_fetcher_cls):
        """【测试 2】网关协同验证：验证针对 Email 账号是否正确拉起 Fetcher，且准确调用了“物理核销已读”机制"""

        # 1. 拦截底层 EmailFetcher 并编排返回值
        mock_fetcher_instance = AsyncMock()
        mock_fetcher_cls.return_value = mock_fetcher_instance

        # 模拟抓取到了 2 封邮件：一封别人发的（需要打已读），一封自己发的（不打已读）
        mock_fetcher_instance.fetch_new.return_value = [
            {"account_msg_id": "ext_mid_1", "is_from_me": False, "source_folder": "INBOX"},
            {"account_msg_id": "my_mid_2", "is_from_me": True, "source_folder": "Sent"}
        ]

        # 2. 触发账号抓取行为
        result_msgs = await fetch_messages_for_account(self.mock_account)

        # 3. 核心断言：
        self.assertEqual(len(result_msgs), 2)

        # 💥 容错护城河验证：确认只对外部发来的邮件（ext_mid_1）调用了 mark_as_processed 核销
        mock_fetcher_instance.mark_as_processed.assert_called_once_with("ext_mid_1", folder="INBOX")
        mock_sleep.assert_called_once_with(1)  # 验证并发保护喘息机制已触发

    @patch("workers.notification.fetch_manager.trigger_email_scan")
    @patch("workers.notification.fetch_manager.SessionLocal")
    @patch("workers.notification.fetch_manager.fetch_messages_for_account")
    @patch("workers.notification.fetch_manager.process_and_save_message")
    @patch("workers.notification.fetch_manager.asyncio.wait_for", new_callable=AsyncMock)
    async def test_fetch_loop_triggers_ai(self, mock_wait_for, mock_process_save, mock_fetch_msgs, mock_session,
                                          mock_trigger_ai):
        """【测试 3】死循环破壁与 AI 唤醒验证：验证大循环在侦测到新数据时，能够精准按响 Email Scheduler 的门铃"""

        # 1. 配置控制大循环的红绿灯
        stop_event = asyncio.Event()
        new_data_event = asyncio.Event()

        # 2. 编排虚拟的数据库和账号查询
        mock_db_instance = MagicMock()
        mock_session.return_value = mock_db_instance
        mock_db_instance.query.return_value.filter.return_value.all.return_value = [self.mock_account]

        # 3. 模拟这轮扫盘抓到了新邮件
        mock_fetch_msgs.return_value = [self.raw_message_data]
        mock_process_save.return_value = MagicMock()  # 模拟入库成功返回对象

        # 4. 巧妙打破死循环：在 wait_for 挂起时，主动把 stop_event 设为 True，让 while 循环只跑一圈就体面退出
        async def mock_wait_behavior(*args, **kwargs):
            stop_event.set()
            raise asyncio.TimeoutError()

        mock_wait_for.side_effect = mock_wait_behavior

        # 5. 执行循环（它只会跑一圈然后被我们的 Mock 叫停）
        await fetch_loop(stop_event, new_data_event, poll_interval=1)

        # 6. 💥 核心联动链路断言：
        # 验证因为拉到了新数据，系统成功按响了唤醒大模型的门铃！
        mock_trigger_ai.assert_called_once()
        self.assertTrue(new_data_event.is_set())

        # 验证数据库连接池被安全关闭，防止内存泄漏
        mock_db_instance.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()