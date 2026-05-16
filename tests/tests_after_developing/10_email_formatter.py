# tests/tests_after_developing/10_email_formatter.py
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime
import sys
import os

# 确保项目根目录在 PYTHONPATH 中，防止单独单点运行时抛出导入错误
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入待测的邮件剧本拼装组件
from app.services.context.email.formatter import EmailFormatter


class TestEmailFormatter(unittest.TestCase):

    def test_extract_pure_reply_empty_and_none(self):
        """【测试 1】边界防御：验证当输入为空值或 None 时，安全返回空字符串，绝不引发红爆异常"""
        self.assertEqual(EmailFormatter.extract_pure_reply(""), "")
        self.assertEqual(EmailFormatter.extract_pure_reply(None), "")

    def test_extract_pure_reply_whitespace_and_regex_compression(self):
        """【测试 2】高级细节打磨：验证 HTML 实体特种空格替换、行首尾修剪、多重连续回车与句子中间多空格压实"""
        # 构造一个包含各种糟糕格式、不可见空白符以及多重回车的极端剧本
        dirty_input = "  第一行开头有空格 \xa0 包含了不可见实体空格 \n\n\n\n 第二行中间有   很多空格  \n\n\n"

        # 触发清洗
        result = EmailFormatter.extract_pure_reply(dirty_input)

        # 断言追溯判定：
        # 1. 开头和结尾的空格必须被无情裁剪
        self.assertTrue(result.startswith("第一行开头有空格"))
        self.assertTrue(result.endswith("很多空格"))
        # 2. \xa0 必须被完美清洗为普通空格，连续的 3 个以上换行符（\n{3,}）必须被压实为双换行（\n\n）
        self.assertNotIn("\n\n\n", result)
        self.assertIn("\n\n", result)
        # 3. 句子中间连续的 3 个空格必须被无缝缩减为 1 个普通空格
        self.assertIn("中间有 很多空格", result)

    @patch("app.services.context.email.formatter.EmailReplyParser.parse_reply")
    def test_extract_pure_reply_parser_crash_fallback(self, mock_parse_reply):
        """【测试 3】第三方库极端崩溃容错：验证当 EmailReplyParser 遭遇未知二进制脏数据爆裂时，系统能弹性降级返回原生文本"""
        # 模拟第三方解析器直接抛出内部严重异常
        mock_parse_reply.side_effect = Exception("Mailgun EmailReplyParser Core Segfault")

        test_text = "  Hello Luke Samuel, this is raw backup text.  "

        # 触发动作
        # 依据设计，顶层 try...except Exception 必须温顺截获炸弹，并返回对原文本进行 .strip() 后的安全字符串
        result = EmailFormatter.extract_pure_reply(test_text)

        self.assertEqual(result, "Hello Luke Samuel, this is raw backup text.")

    def test_format_email_script_empty_input(self):
        """【测试 4】剧本组装边界：验证当历史邮件记录列表为空时，直接平稳返回空字符串"""
        self.assertEqual(EmailFormatter.format_email_script([]), "")
        self.assertEqual(EmailFormatter.format_email_script(None), "")

    def test_format_email_script_single_message_no_context(self):
        """【测试 5】第一封信无历史背景场景：验证当只有一封新邮件时，自动跳过【对话背景】区，仅高亮渲染最新诉求区"""
        # 1. 构造单封压轴邮件模型
        mock_msg = MagicMock()
        mock_msg.subject = "PA2552 Automation Testing Help"
        mock_msg.is_from_me = False
        mock_msg.sender = "classmate@bth.se"
        mock_msg.received_at = datetime(2026, 5, 15, 18, 0)
        mock_msg.cleaned_content = "Can you show me your Page Object Model setup?"

        # 2. 触发剧本生成
        script = EmailFormatter.format_email_script([mock_msg])

        # 3. 断言校验
        self.assertIsNotNone(script)
        self.assertIn("【邮件主题: PA2552 Automation Testing Help】", script)
        # 💥 关键策略隔离断言：由于无历史包袱，整个生成的剧本流中绝对不准包含【对话背景】字样与华丽分割线
        self.assertNotIn("【对话背景 (Context)】", script)
        self.assertNotIn("-" * 40, script)

        # 校验最新区字段渲染是否精准
        self.assertIn("【！！当前待处理邮件 (LATEST MESSAGE)！！】", script)
        self.assertIn("发件人: classmate@bth.se", script)
        self.assertIn("正文诉求:\nCan you show me your Page Object Model setup?", script)

    def test_format_email_script_with_full_conversation_history(self):
        """【压力测试 6】完整来回多维长对话剧本：验证包含了历史往来（我方发信、对方来信）时的全量剧本拼装，分割线以及时间格式化"""
        # 1. 构造最古老的历史背景信件 (对方来信)
        msg_oldest = MagicMock()
        msg_oldest.subject = "MS1411 Project Extension"
        msg_oldest.is_from_me = False
        msg_oldest.sender = "coordinator@bth.se"
        msg_oldest.received_at = datetime(2026, 5, 14, 9, 0)
        msg_oldest.cleaned_content = "Hi Luke, did you finish the MS1411 code?"

        # 2. 构造中层历史背景信件 (我方回复回声)
        msg_reply = MagicMock()
        msg_reply.subject = "MS1411 Project Extension"
        msg_reply.is_from_me = True  # 标记为我发的
        msg_reply.sender = "luke@bth.se"
        msg_reply.received_at = datetime(2026, 5, 14, 10, 30)
        msg_reply.cleaned_content = "Yes, it is already pushed to GitHub repo CZ."

        # 3. 构造当前最新最新收到的压轴待处理信件 (对方再次来信)
        msg_latest = MagicMock()
        msg_latest.subject = "MS1411 Project Extension"
        msg_latest.is_from_me = False
        msg_latest.sender = "coordinator@bth.se"
        msg_latest.received_at = datetime(2026, 5, 15, 14, 0)
        msg_latest.cleaned_content = "Perfect! I will review it today."

        # 拼装时间有序的正序列表
        conversation_flow = [msg_oldest, msg_reply, msg_latest]

        # 执行动作
        final_script = EmailFormatter.format_email_script(conversation_flow)

        # 4. 全链路业务级强力断言：
        self.assertIn("【邮件主题: MS1411 Project Extension】", final_script)

        # 历史区核心校验：
        self.assertIn("【对话背景 (Context)】", final_script)
        # 校验对方来信时的昵称格式化
        self.assertIn("[2026-05-14 09:00] coordinator@bth.se: Hi Luke, did you finish the MS1411 code?", final_script)
        # 校验我方回声消息时自动更迭翻译为“我”的语义
        self.assertIn("[2026-05-14 10:30] 我: Yes, it is already pushed to GitHub repo CZ.", final_script)

        # 💥 分割线护栏断言：历史与最新消息交界处，必须包含 40 个连字符拼成的物理防干扰线
        self.assertIn("-" * 40, final_script)

        # 最新高亮区校验：
        self.assertIn("【！！当前待处理邮件 (LATEST MESSAGE)！！】", final_script)
        self.assertIn("发件人: coordinator@bth.se", final_script)
        self.assertIn("时间: 2026-05-15 14:00", final_script)
        self.assertIn("正文诉求:\nPerfect! I will review it today.", final_script)


# 💥 挂载标准单元测试启动飞轮，允许直接一键点击一键运行
if __name__ == "__main__":
    unittest.main()