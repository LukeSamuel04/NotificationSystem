# workers/notification/fetchers/email_fetcher.py
import email
import re
import uuid
from email.header import decode_header
from email.message import Message
from email.utils import parseaddr
from typing import List, Dict, Any

import aioimaplib  # 原生异步 IMAP 引擎
from workers.notification.fetchers.base import BaseFetcher


class EmailFetcher(BaseFetcher):
    """
    基于原生异步 (Asyncio + aioimaplib) 的极速邮件抓取引擎。
    完美适配 QQ 邮箱严格 LIST 语法、物理即时打标与双向对话流闭环。
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            self.host = config["host"]
            self.user = config["user"]
            self.password = config["password"]
        except KeyError as e:
            raise ValueError(f"初始化 EmailFetcher 失败，缺少必要的配置项: {e}")

    async def test_connection(self) -> bool:
        print(f"🔄 [异步探针] 正在验证邮箱账号: {self.user} ...")
        client = None
        try:
            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()

            # 💥 核心修复：捕获响应对象并检查认证结果
            response = await client.login(self.user, self.password)

            if response.result == 'OK':
                print(f"✅ 邮箱验证通过: {self.user}")
                await client.logout()
                return True
            else:
                # 专门拦截 163 等返回 NO 但不抛出异常的情况
                print(f"❌ 邮箱验证失败 ({response.result}): {response.lines}")
                return False
        except Exception as e:
            print(f"❌ 邮箱验证发生异常: {e}")
            return False
        finally:
            # 确保无论成功失败都能安全关闭连接
            if client:
                try:
                    await client.logout()
                except:
                    pass

    async def fetch_new(self) -> List[Dict[str, Any]]:
        messages = []
        try:
            print(f"🌐 正在异步连接到 {self.host} 抓取 {self.user} 的双向邮件...")

            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()
            await client.login(self.user, self.password)

            # 💥 终极修复：注入带实体引号的字面量参数，完美攻克 QQ 邮箱 BAD 响应壁垒
            status, folder_list = await client.list('""', '"*"')
            available_folders = [f.decode(errors="ignore") for f in folder_list] if status == "OK" else []

            target_folders = ["INBOX"]

            # 精准提取真实的 Sent 文件夹名称
            sent_folder_name = None
            for raw_folder_str in available_folders:
                folder_lower = raw_folder_str.lower()
                if any(key in folder_lower for key in ["sent", "已发送", "sent messages"]):
                    # 提取末尾双引号内的确切物理路径名称
                    match = re.search(r'"([^"]+)"$', raw_folder_str)
                    if match:
                        sent_folder_name = match.group(1)
                    else:
                        sent_folder_name = raw_folder_str.split(' "/" ')[-1].strip('"')
                    break

            if sent_folder_name:
                target_folders.append(sent_folder_name)
                print(f"📍 成功锁定发件箱真实目录: [{sent_folder_name}]")
            else:
                print("⚠️ 未能匹配到发件箱目录，保留收件箱单行道收取。")

            # 遍历目标文件夹逐个收取
            for folder in target_folders:
                # 带有空格的文件夹（如 Sent Messages）必须用双引号包裹 select
                await client.select(f'"{folder}"')

                if folder == "INBOX":
                    status, response = await client.search('UNSEEN')
                    email_ids = response[0].split() if status == "OK" and response[0] else []
                else:
                    # 针对发件箱拉取最后 20 封信件索引，用于构建熟肉上下文
                    status, response = await client.search('ALL')
                    email_ids = response[0].split()[-20:] if status == "OK" and response[0] else []

                if email_ids:
                    print(f"[{self.user}] 正在目录 [{folder}] 消费 {len(email_ids)} 封目标报文...")

                for e_id in email_ids:
                    fetch_status, fetch_data = await client.fetch(e_id.decode('utf-8'), '(RFC822)')

                    if fetch_status == "OK":
                        raw_email = fetch_data[1]
                        msg = email.message_from_bytes(raw_email)

                        raw_msg_id = msg.get("Message-ID", "")
                        account_msg_id = raw_msg_id.strip("<>") if raw_msg_id else f"no_id_{uuid.uuid4().hex[:8]}"

                        sender_name, external_sender_id = parseaddr(msg.get("From", ""))
                        if not sender_name:
                            sender_name = external_sender_id

                        is_from_me = (external_sender_id.lower() == self.user.lower())
                        subject_text = self._clean_subject(msg.get("Subject", "无主题"))

                        messages.append({
                            "platform": "email",
                            "account_msg_id": account_msg_id,
                            "reply_to_mid": (msg.get("In-Reply-To") or "").strip("<>") or None,
                            "sender": sender_name,
                            "external_sender_id": external_sender_id,
                            "subject": subject_text,
                            "content": self._extract_body(msg),
                            "is_from_me": is_from_me,
                            "source_folder": folder
                        })

                        # 💥 物理级光速核销已读状态
                        if folder == "INBOX" and not is_from_me:
                            await client.store(e_id.decode('utf-8'), '+FLAGS', '\\Seen')
                            print(f"✨ [物理打标] 已读核销成功 ➔ {subject_text[:20]}...")

            await client.close()
            await client.logout()

        except Exception as e:
            print(f"⚠️ [{self.user}] 底层通信中断: {str(e)}")

        return messages

    async def mark_as_processed(self, account_msg_id: str, folder: str = "INBOX"):
        """向下兼容的冗余层打标器"""
        try:
            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()
            await client.login(self.user, self.password)
            await client.select(f'"{folder}"')

            status, response = await client.search(f'HEADER Message-ID "<{account_msg_id}>"')
            if not (status == "OK" and response[0]):
                status, response = await client.search(f'HEADER Message-ID "{account_msg_id}"')

            if status == "OK" and response[0]:
                for e_id in response[0].split():
                    await client.store(e_id.decode('utf-8'), '+FLAGS', '\\Seen')

            await client.close()
            await client.logout()
        except Exception:
            pass

    def _extract_body(self, msg: Message) -> str:
        body_html = ""
        body_plain = ""

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    body_html = part.get_payload(decode=True).decode(errors="ignore")
                elif content_type == "text/plain":
                    body_plain = part.get_payload(decode=True).decode(errors="ignore")
        else:
            content_type = msg.get_content_type()
            if content_type == "text/html":
                body_html = msg.get_payload(decode=True).decode(errors="ignore")
            elif content_type == "text/plain":
                body_plain = msg.get_payload(decode=True).decode(errors="ignore")

        return body_html if body_html else body_plain

    def _clean_subject(self, raw_subject: str) -> str:
        decoded_subject = ""
        for part, encoding in decode_header(raw_subject):
            if isinstance(part, bytes):
                decoded_subject += part.decode(encoding or "utf-8", errors="ignore")
            else:
                decoded_subject += part
        return re.sub(r'(?i)^(re|fwd|fw|回复|转发)\s*:\s*', '', decoded_subject).strip()