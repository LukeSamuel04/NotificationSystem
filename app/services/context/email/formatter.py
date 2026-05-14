# app/services/context/email/formatter.py
import logging
import re
from email_reply_parser import EmailReplyParser

logger = logging.getLogger("EmailFormatter")


class EmailFormatter:

    @staticmethod
    def extract_pure_reply(cleaned_content: str) -> str:
        """
        逻辑切割与终极压缩：
        1. 使用 Mailgun 算法一刀斩断历史引用记录和签名档。
        2. 使用正则深度压缩连续空行和冗余空白符。
        """
        if not cleaned_content:
            return ""

        try:
            # 1. 直接使用神器进行深度提纯 (砍掉签名档和引用历史)
            pure_reply = EmailReplyParser.parse_reply(cleaned_content)

            # 2. 终极空白符洗礼 (打磨细节)
            # 替换特殊的不可见字符 (如 \xa0 即 HTML 中的 &nbsp;) 为普通空格
            text = pure_reply.replace('\xa0', ' ')

            # 清理每一行首尾的空格，防止出现“只有空格的假空行”影响后续正则
            lines = [line.strip() for line in text.split('\n')]
            text = '\n'.join(lines)

            # 将 3 个及以上的连续换行符压缩为 2 个 (仅保留正常的段落间距)
            text = re.sub(r'\n{3,}', '\n\n', text)

            # 将句子中间连续的多个空格压缩为 1 个
            text = re.sub(r' {2,}', ' ', text)

            return text.strip()

        except Exception as e:
            logger.error(f"❌ 邮件签名切割过程发生异常: {e}")
            return cleaned_content.strip()

    @staticmethod
    def format_email_script(email_records: list) -> str:
        """
        将数据库捞出来的一组邮件，拼装成分层清晰的 AI 剧本。
        期望传入的 email_records 是按时间正序 (最早的在前，最新的在最后) 排列的。
        """
        if not email_records:
            return ""

        # 核心逻辑：切分历史记录和最新邮件
        latest_msg = email_records[-1]  # 列表最后一个元素是最新进来的邮件
        history_msgs = email_records[:-1]  # 前面的所有元素都是历史背景

        script_lines = []

        # 1. 提取全局主题
        subject = latest_msg.subject or "无主题"
        script_lines.append(f"【邮件主题: {subject}】\n")

        # 2. 拼装历史背景区 (如果没有历史邮件，这部分自动跳过)
        if history_msgs:
            script_lines.append("【对话背景 (Context)】")
            for msg in history_msgs:
                sender_name = "我" if msg.is_from_me else (msg.sender or "发件人")
                time_str = msg.received_at.strftime("%Y-%m-%d %H:%M") if msg.received_at else "未知时间"

                # 调用逻辑切割器，把历史记录提纯
                clean_reply = EmailFormatter.extract_pure_reply(msg.cleaned_content)
                script_lines.append(f"[{time_str}] {sender_name}: {clean_reply}")

            script_lines.append("\n" + "-" * 40 + "\n")  # 加一条华丽的分割线

        # 3. 拼装高亮的最新邮件区
        script_lines.append("【！！当前待处理邮件 (LATEST MESSAGE)！！】")
        latest_sender = "我" if latest_msg.is_from_me else (latest_msg.sender or "发件人")
        latest_time = latest_msg.received_at.strftime("%Y-%m-%d %H:%M") if latest_msg.received_at else "未知时间"
        latest_clean = EmailFormatter.extract_pure_reply(latest_msg.cleaned_content)

        script_lines.append(f"发件人: {latest_sender}")
        script_lines.append(f"时间: {latest_time}")
        script_lines.append(f"正文诉求:\n{latest_clean}\n")

        return "\n".join(script_lines)