# tests/tests_after_developing/13_test_email_context_manager.py
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session

# 导入待测的 Manager 以及依赖模型
from app.services.context.email.manager import get_email_formatted_context
from app.models.notifications import Notification


class TestEmailContextManager(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：构造基础的依赖对象"""
        self.mock_db = MagicMock(spec=Session)

        # 构造当前待处理的邮件通知实体
        self.mock_notification = MagicMock(spec=Notification)
        self.mock_notification.cleaned_content = "This is a critical bug report for the backend."

    @patch("app.services.context.email.manager.EmailFormatter")
    @patch("app.services.context.email.manager.EmailContextFinder")
    async def test_manager_success_pipeline_flow(self, mock_finder, mock_formatter):
        """【测试 1】主线流调配验证：验证 Manager 是否精准串联了 Finder 和 Formatter，并没有发生数据截断"""

        # 1. 模拟 Finder 成功捞出了历史列表
        mock_context_list = [MagicMock(), self.mock_notification]
        mock_finder.get_context_records.return_value = mock_context_list

        # 2. 模拟 Formatter 成功将其渲染为剧本字符串
        expected_script = "【对话背景】... 【最新邮件诉求】..."
        mock_formatter.format_email_script.return_value = expected_script

        # 3. 触发 Manager 调度
        result = await get_email_formatted_context(self.mock_db, self.mock_notification)

        # 4. 胶水层核心断言：
        # 确保 Manager 把 db 和 notification 原封不动地交给了 Finder
        mock_finder.get_context_records.assert_called_once_with(self.mock_db, self.mock_notification)

        # 确保 Manager 把 Finder 吐出的列表原封不动交给了 Formatter
        mock_formatter.format_email_script.assert_called_once_with(mock_context_list)

        # 确保最终 Manager 返回的是 Formatter 渲染的字符串
        self.assertEqual(result, expected_script)

    @patch("app.services.context.email.manager.EmailFormatter")
    @patch("app.services.context.email.manager.EmailContextFinder")
    async def test_manager_exception_fallback_safety_net(self, mock_finder, mock_formatter):
        """【测试 2】熔断兜底验证：验证当底层数据库彻底崩溃或计算溢出时，Manager 能够死死兜住异常，返回仅包含当前邮件的降级剧本"""

        # 1. 模拟 Finder 遭遇了毁灭性的底层数据库异常（如连接池打满、网络断开）
        mock_finder.get_context_records.side_effect = Exception("Critical Database Connection Timeout")

        # 2. 触发 Manager 调度
        result = await get_email_formatted_context(self.mock_db, self.mock_notification)

        # 3. 容错防线断言：
        mock_finder.get_context_records.assert_called_once()
        # 因为 Finder 炸了，程序绝不应该再继续走到 Formatter 浪费 CPU
        mock_formatter.format_email_script.assert_not_called()

        # 💥 核心断言：验证系统并没有崩溃（没有抛出红爆异常），而是成功触发了兜底降级方案
        expected_fallback = f"【最新邮件诉求】:\n{self.mock_notification.cleaned_content}"
        self.assertEqual(result, expected_fallback)


# 💥 挂载标准单元测试启动入口
if __name__ == "__main__":
    unittest.main()