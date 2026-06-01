# workers/notification/fetchers/email_fetcher.py
import email
import asyncio
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
    已彻底修复 GBK/GB2312 中文乱码与 Base64 MIME 头部解析天坑。
    """

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        try:
            self.host = config["host"]
            self.user = config["user"]
            self.password = config["password"]
        except KeyError as e:
            raise ValueError(f"初始化 EmailFetcher 失败，缺少必要的配置项: {e}")

    # ==========================================
    # 💥 核心修复一：专门对付乱码的头部解码器
    # ==========================================
    def _decode_mail_header(self, header_text: str) -> str:
        """专门处理 =?GBK?B?...?= 这种邮件头部复杂编码"""
        if not header_text:
            return ""
        decoded_fragments = decode_header(header_text)
        header_str = ""
        for fragment, charset in decoded_fragments:
            if isinstance(fragment, bytes):
                # 国内邮箱经常标称 gb2312，但实际上包含 gbk 扩展字符 (如各种生僻字)
                charset = charset or 'utf-8'
                if charset.lower() == 'gb2312':
                    charset = 'gbk'
                try:
                    header_str += fragment.decode(charset, errors='replace')
                except Exception:
                    # 兜底强解
                    header_str += fragment.decode('utf-8', errors='replace')
            else:
                header_str += str(fragment)
        return header_str

    async def test_connection(self) -> bool:
        print(f"🔄 [异步探针] 正在验证邮箱账号: {self.user} ...")
        client = None
        try:
            client = aioimaplib.IMAP4_SSL(host=self.host)
            await client.wait_hello_from_server()

            response = await client.login(self.user, self.password)

            if response.result == 'OK':
                print(f"✅ 邮箱验证通过: {self.user}")
                return True
            else:
                print(f"❌ 邮箱验证失败 ({response.result}): {response.lines}")
                return False
        except Exception as e:
            print(f"❌ 邮箱验证发生异常: {e}")
            return False
        finally:
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

            status, folder_list = await client.list('""', '"*"')
            available_folders = [f.decode(errors="ignore") for f in folder_list] if status == "OK" else []

            target_folders = ["INBOX"]

            sent_folder_name = None
            for raw_folder_str in available_folders:
                folder_lower = raw_folder_str.lower()
                if any(key in folder_lower for key in ["sent", "已发送", "sent messages"]):
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

            for folder in target_folders:
                await client.select(f'"{folder}"')

                if folder == "INBOX":
                    status, response = await client.search('UNSEEN')
                    email_ids = response[0].split() if status == "OK" and response[0] else []
                else:
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

                        # 💥 应用头部解码器：解决发件人名字 (周乐田) 变成 =?GBK?B?... 乱码的问题
                        raw_from = msg.get("From", "")
                        raw_sender_name, external_sender_id = parseaddr(raw_from)
                        sender_name = self._decode_mail_header(raw_sender_name)

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

                        if folder == "INBOX" and not is_from_me:
                            await client.store(e_id.decode('utf-8'), '+FLAGS', '\\Seen')
                            print(f"✨ [物理打标] 已读核销成功 ➔ {subject_text[:20]}...")

            await asyncio.sleep(0.1)
            await client.close()
            await client.logout()

        except Exception as e:
            print(f"⚠️ [{self.user}] 底层通信中断: {str(e)}")

        return messages

    async def mark_as_processed(self, account_msg_id: str, folder: str = "INBOX"):
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

    # ==========================================
    # 💥 核心修复二：动态 Charset 嗅探与正文提取
    # ==========================================
    def _extract_body(self, msg: Message) -> str:
        body_html = ""
        body_plain = ""

        # 内部封装一个带动态编码识别的解码器
        def decode_payload(part) -> str:
            raw_payload = part.get_payload(decode=True)
            if not raw_payload:
                return ""

            # 关键：让邮件自己告诉你它是哪种字符集
            charset = part.get_content_charset() or 'utf-8'

            # 填平天坑：把狭隘的 gb2312 强制提升为宽容的 gbk
            if charset.lower() == 'gb2312':
                charset = 'gbk'

            try:
                return raw_payload.decode(charset, errors='ignore')
            except LookupError:
                return raw_payload.decode('utf-8', errors='ignore')

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/html":
                    body_html = decode_payload(part)
                elif content_type == "text/plain":
                    body_plain = decode_payload(part)
        else:
            content_type = msg.get_content_type()
            if content_type == "text/html":
                body_html = decode_payload(msg)
            elif content_type == "text/plain":
                body_plain = decode_payload(msg)

        return body_html if body_html else body_plain

    def _clean_subject(self, raw_subject: str) -> str:
        # 💥 应用头部解码器：彻底解决主题乱码
        decoded_subject = self._decode_mail_header(raw_subject)
        return re.sub(r'(?i)^(re|fwd|fw|回复|转发)\s*:\s*', '', decoded_subject).strip()