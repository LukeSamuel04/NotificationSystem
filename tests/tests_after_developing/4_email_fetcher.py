# tests/tests_after_developing/test_email_fetcher.py
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import email

# 导入待测抓取引擎核心类
from workers.notification.fetchers.email_fetcher import EmailFetcher


class TestEmailFetcher(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：构造一套标准的虚拟邮箱配置参数"""
        self.mock_config = {
            "host": "imap.bth.se",
            "user": "luke@bth.se",
            "password": "mock_secret_token_2026"
        }
        # 实例化待测对象
        self.fetcher = EmailFetcher(self.mock_config)

    @patch("workers.notification.fetchers.email_fetcher.aioimaplib.IMAP4_SSL")
    async def test_test_connection_success(self, mock_imap_cls):
        """【测试 1】验证：当邮箱服务器握手且登录成功(OK)时，探针正确返回 True"""
        # 1. 模拟复杂的 aioimaplib 客户端实例行为
        mock_client = AsyncMock()
        mock_imap_cls.return_value = mock_client

        # 模拟登录返回响应：response.result == 'OK'
        mock_response = MagicMock()
        mock_response.result = "OK"
        mock_client.login.return_value = mock_response

        # 2. 执行可用性探测
        result = await self.fetcher.test_connection()

        # 3. 核心断言
        self.assertTrue(result)
        mock_client.wait_hello_from_server.assert_called_once()
        mock_client.login.assert_called_once_with("luke@bth.se", "mock_secret_token_2026")
        mock_client.logout.assert_called_once()

    @patch("workers.notification.fetchers.email_fetcher.aioimaplib.IMAP4_SSL")
    async def test_test_connection_failed_by_auth(self, mock_imap_cls):
        """【测试 2】验证：当邮箱密码或授权码错误(NO)时，探针弹性容错返回 False"""
        mock_client = AsyncMock()
        mock_imap_cls.return_value = mock_client

        # 模拟授权失败：response.result == 'NO'
        mock_response = MagicMock()
        mock_response.result = "NO"
        mock_response.lines = [b"Authentication failed"]
        mock_client.login.return_value = mock_response

        # 执行探测
        result = await self.fetcher.test_connection()

        # 核心断言：必须安全返回 False，不准向上抛出异常崩溃
        self.assertFalse(result)

    @patch("workers.notification.fetchers.email_fetcher.aioimaplib.IMAP4_SSL")
    async def test_fetch_new_comprehensive_workflow(self, mock_imap_cls):
        """
        【测试 3】核心数据流闭环断言：
        验证整个抓取管道（连接、解析收发件箱目录、捕获未读报文、解构提取纯文本、物理标记已读）完整无误。
        """
        mock_client = AsyncMock()
        mock_imap_cls.return_value = mock_client

        # 1. Mock 模拟 client.list() 吐出的邮箱原始可用目录流（测试你的真实发件箱锁定正则）
        mock_client.list.return_value = ("OK", [
            b'(\\HasNoChildren) "/" "INBOX"',
            b'(\\HasNoChildren) "/" "Sent Messages"'  # 用于测试发件箱自动定位机制
        ])

        # 2. Mock 模拟 client.search() 吐出的邮件物理唯一整型 ID 编号
        # 让收件箱搜出 1 封信（ID: 101），发件箱搜出 1 封信（ID: 202）
        mock_client.search.side_effect = [
            ("OK", [b"101"]),  # 第一次被 INBOX 触发
            ("OK", [b"202"])  # 第二次被 Sent Messages 触发
        ]

        # 3. 动态构造真实的符合 RFC822 标准的 Email 字节流报文
        # 模拟收件箱报文 (来自导师的紧急通知)
        raw_email_bytes = (
            b"From: professor@bth.se\n"
            b"Subject: =?utf-8?B?UEEyNTUyIEFzc2lnbm1lbnQgUmVtaW5kZXI=?=\n"  # Base64 编码的学业主题
            b"Message-ID: <bth-course-assignment-id-2026>\n"
            b"Content-Type: text/plain; charset=utf-8\n\n"
            b"Hi Luke, please verify your Selenium automated test cases run smoothly."
        )

        # 让 client.fetch 成功吐出此原始数据
        mock_client.fetch.return_value = ("OK", [None, raw_email_bytes])

        # 4. 执行全管道抓取调度
        fetched_messages = await self.fetcher.fetch_new()

        # 5. 全链路闭环核心断言：
        self.assertIsNotNone(fetched_messages)
        self.assertEqual(len(fetched_messages), 2)  # 收发两封信均应被捞出

        # 6. 深入断言第 1 封被 AI 提取清洗后的熟肉字典字典数据
        mail_data = fetched_messages[0]
        self.assertEqual(mail_data["platform"], "email")
        self.assertEqual(mail_data["account_msg_id"], "bth-course-assignment-id-2026")
        self.assertEqual(mail_data["sender"], "professor@bth.se")
        self.assertEqual(mail_data["subject"], "PA2552 Assignment Reminder")  # 验证 _clean_subject 解码器生效
        self.assertIn("Selenium automated test cases", mail_data["content"])  # 验证 _extract_body 提取器生效
        self.assertFalse(mail_data["is_from_me"])  # 外部来信

        # 7. 💥 生产安全断言：验证是否对收件箱的外部未读邮件执行了物理打标核销已读
        mock_client.store.assert_called_once_with("101", "+FLAGS", "\\Seen")

        # 8. 确保整个事务生命周期内最后优雅退出了登录，释放连接池
        mock_client.close.assert_called_once()
        mock_client.logout.assert_called_once()


# 💥 挂载标准单元测试启动飞轮，允许直接一键点击点击运行
if __name__ == "__main__":
    unittest.main()