import email
from email.header import decode_header
from email.message import Message
from typing import List, Dict, Any

import aioimaplib  # 原生异步 IMAP 引擎
from workers.notification.fetchers.base import BaseFetcher


class EmailFetcher(BaseFetcher):
    """
    基于纯原生异步 (Asyncio + aioimaplib) 的极速邮件抓取引擎。
    """

    def __init__(self, config: Dict[str, Any]):
        # 1. 向上汇报，完成基础类的初始化
        super().__init__(config)

        # 2. 提取子类专属变量（Fail-Fast 机制）
        try:
            self.host = config["host"]
            self.user = config["user"]
            self.password = config["password"]
        except KeyError as e:
            raise ValueError(f"初始化 EmailFetcher 失败，缺少必要的配置项: {e}")

    # ==========================================
    # 履行契约 1：验证连接
    # ==========================================
    async def test_connection(self) -> bool:
        print(f"🔄 [异步探针] 正在验证邮箱账号: {self.user} ...")
        try:
            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()
            await client.login(self.user, self.password)
            await client.logout()
            print("✅ 邮箱验证通过！")
            return True
        except Exception as e:
            print(f"❌ 邮箱验证失败: {e}")
            return False

    # ==========================================
    # 履行契约 2：极速异步抓取
    # ==========================================
    async def fetch_new(self) -> List[Dict[str, Any]]:
        messages = []
        try:
            print(f"🌐 正在异步连接到 {self.host} 抓取 {self.user} 的新邮件...")

            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()
            await client.login(self.user, self.password)
            await client.select("INBOX")

            status, response = await client.search('UNSEEN')

            if status == "OK" and response[0]:
                email_ids = response[0].split()
                print(f"[{self.user}] 发现 {len(email_ids)} 封新邮件")

                for e_id in email_ids:
                    fetch_status, fetch_data = await client.fetch(e_id.decode('utf-8'), '(RFC822)')

                    if fetch_status == "OK":
                        raw_email = fetch_data[1]
                        msg = email.message_from_bytes(raw_email)

                        subject, encoding = decode_header(msg["Subject"])[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8")

                        messages.append({
                            "platform": "email",
                            "msg_id": e_id.decode('utf-8'),
                            "sender": msg.get("From"),
                            "subject": subject,
                            "content": self._extract_body(msg)
                        })

            await client.logout()

        except Exception as e:
            print(f"⚠️ [{self.user}] 异步抓取过程中发生错误: {str(e)}")

        return messages

    # ==========================================
    # 履行契约 3：异步标记已读
    # ==========================================
    async def mark_as_processed(self, message_id: str):
        try:
            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()
            await client.login(self.user, self.password)
            await client.select("INBOX")
            await client.store(message_id, '+FLAGS', '\\Seen')
            await client.logout()
            print(f"✨ 成功将邮件 {message_id} 标记为已读。")
        except Exception as e:
            print(f"⚠️ 标记邮件 {message_id} 失败: {str(e)}")

    def _extract_body(self, msg: Message) -> str:
        """解析邮件正文的工具方法 (纯 CPU 运算)"""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors="ignore")
        else:
            return msg.get_payload(decode=True).decode(errors="ignore")
        return ""