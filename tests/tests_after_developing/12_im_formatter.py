# tests/tests_after_developing/12_test_im_formatter.py
import unittest
from unittest.mock import MagicMock
from datetime import datetime

# 导入待测同步组件
from app.services.context.im.formatter import format_notification_context
from app.models.notifications import Notification


class TestIMContextFormatter(unittest.TestCase):

    def test_format_empty_and_boundary_input(self):
        """【极端边界测试 1】无水之源：验证传入空列表时，直接安全返回空换行串，绝不报 KeyError/AttributeError"""
        self.assertEqual(format_notification_context([]), "")

    def test_format_missing_received_at_timestamp(self):
        """【极端案例测试 2】时间黑洞：验证当某条突发消息因系统偶发抖动缺失时间戳时，降级输出为“未知时间”，不引发程序罢工"""
        mock_msg = MagicMock(spec=Notification)
        mock_msg.account_msg_id = "msg_001"
        mock_msg.is_from_me = False
        mock_msg.received_at = None  # 💥 故意不给时间戳
        mock_msg.reply_to_mid = None
        mock_msg.cleaned_content = "Luke, did you push the Selenium Page Object Model suite?"

        result = format_notification_context([mock_msg])

        # 断言判定：必须用“未知时间”温顺代填
        self.assertIn("[未知时间] 对方：Luke, did you push the Selenium Page Object Model suite?", result)

    def test_format_reply_anchor_missing_in_current_slice(self):
        """【极端案例测试 3】无头引用链：验证被引用的父消息不在本次切片列表内时，触发二级兜底提示词"""
        mock_msg = MagicMock(spec=Notification)
        mock_msg.account_msg_id = "msg_002"
        mock_msg.is_from_me = True
        mock_msg.received_at = datetime(2026, 5, 15, 19, 30, 0)
        mock_msg.reply_to_mid = "ghost_parent_mid_999"  # 💥 引用的 ID 根本不在接下来的 map 里
        mock_msg.cleaned_content = "Yes, already pushed."

        result = format_notification_context([mock_msg])

        # 断言判定：触发第二级兜底语义
        self.assertIn("[2026-05-15 19:30] 我 (回复了之前的一条消息)：Yes, already pushed.", result)

    def test_format_comprehensive_interactive_chat_script(self):
        """【压力测试 4】全功能双向对齐剧本：验证包含了父子精准时间回溯、角色前缀转换、多行组合渲染的生产全量流"""
        # 1. 构造一条历史父消息 (对方发的)
        msg_parent = MagicMock(spec=Notification)
        msg_parent.account_msg_id = "parent_mid_777"
        msg_parent.is_from_me = False
        msg_parent.received_at = datetime(2026, 5, 15, 18, 0, 0)
        msg_parent.reply_to_mid = None
        msg_parent.cleaned_content = "Wanna eat Thai chicken curry tonight?"

        # 2. 构造一条回复它的子消息 (我回复的)
        msg_child = MagicMock(spec=Notification)
        msg_child.account_msg_id = "child_mid_888"
        msg_child.is_from_me = True  # 我发的
        msg_child.received_at = datetime(2026, 5, 15, 18, 15, 0)
        msg_child.reply_to_mid = "parent_mid_777"  # 💥 精准指向父级
        msg_child.cleaned_content = "Sounds great! See you at Willys Karlskrona."

        # 组装对话列表
        notifications_list = [msg_parent, msg_child]

        # 执行格式化
        final_script = format_notification_context(notifications_list)

        # 3. 核心业务级强力断言：
        # 验证行数是否拼装正确
        lines = final_script.split("\n")
        self.assertEqual(len(lines), 2)

        # 验证第一行（对方）
        self.assertIn("[2026-05-15 18:00] 对方：Wanna eat Thai chicken curry tonight?", lines[0])
        # 验证第二行（我 + 💥 高级精准提示词追踪）
        self.assertIn(
            "[2026-05-15 18:15] 我 (回复了 2026-05-15 18:00 的一条消息)：Sounds great! See you at Willys Karlskrona.",
            lines[1])


if __name__ == "__main__":
    unittest.main()