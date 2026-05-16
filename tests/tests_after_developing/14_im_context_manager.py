# tests/tests_after_developing/14_test_im_context_manager.py
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.orm import Session
from app.models.notifications import Notification
from app.services.context.im.manager import get_im_formatted_context


class TestIMContextManager(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：构造基础的依赖对象"""
        self.mock_db = MagicMock(spec=Session)

        # 构造当前待处理的 IM 消息实体
        self.mock_notification = MagicMock(spec=Notification)
        self.mock_notification.cleaned_content = "Hey Luke, are you coming to the gym today?"

    @patch("app.services.context.im.manager.format_notification_context")
    @patch("app.services.context.im.manager.get_im_context", new_callable=AsyncMock)
    async def test_im_manager_success_pipeline_flow(self, mock_get_context, mock_formatter):
        """【测试 1】主线流调配验证：验证 Manager 是否精准串联了异步检索和同步格式化，并没有发生数据丢失"""

        # 1. 模拟底层 Finder 成功捞出了 IM 的双层跳跃历史列表
        mock_context_list = [MagicMock(), self.mock_notification]
        mock_get_context.return_value = mock_context_list

        # 2. 模拟 Formatter 成功将其渲染为带时间前缀的剧本字符串
        expected_script = "[2026-05-16 10:00] 对方：Wanna workout?\n[2026-05-16 10:05] 对方：Hey Luke, are you coming to the gym today?"
        mock_formatter.return_value = expected_script

        # 3. 触发 Manager 调度
        result = await get_im_formatted_context(self.mock_db, self.mock_notification)

        # 4. 胶水层核心断言：
        # 确保 Manager 把 db 和 notification 原封不动地交给了异步的 get_im_context
        mock_get_context.assert_called_once_with(self.mock_db, self.mock_notification)

        # 确保 Manager 把异步检索出来的列表交给了同步的 format_notification_context
        mock_formatter.assert_called_once_with(mock_context_list)

        # 确保最终 Manager 返回的是 Formatter 渲染的字符串
        self.assertEqual(result, expected_script)

    @patch("app.services.context.im.manager.format_notification_context")
    @patch("app.services.context.im.manager.get_im_context", new_callable=AsyncMock)
    async def test_im_manager_exception_fallback_safety_net(self, mock_get_context, mock_formatter):
        """【测试 2】熔断兜底验证：验证当底层双层检索发生致命报错时，Manager 能够兜住异常并返回降级内容"""

        # 1. 模拟 Finder 在进行高难度递归查询时，遭遇了数据库断开或严重超时
        mock_get_context.side_effect = Exception("Navicat Deadlock during IM Context Propagation")

        # 2. 触发 Manager 调度
        result = await get_im_formatted_context(self.mock_db, self.mock_notification)

        # 3. 容错防线断言：
        mock_get_context.assert_called_once()

        # 因为 Finder 炸了，程序绝不应该继续执行 Formatter 进行无效拼装
        mock_formatter.assert_not_called()

        # 💥 核心断言：验证系统防崩溃盾牌生效，返回了符合 IM 口径的极简保底剧本
        expected_fallback = f"【消息内容】: {self.mock_notification.cleaned_content}"
        self.assertEqual(result, expected_fallback)


# 💥 挂载标准单元测试启动入口
if __name__ == "__main__":
    unittest.main()