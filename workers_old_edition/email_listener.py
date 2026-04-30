import time
import imaplib
import email
from email.header import decode_header
import requests

# ================= 极简硬编码测试区 =================
# 跑通之后，这里的东西明天全都会进 SQL 数据库！
IMAP_SERVER = "imap.qq.com"
EMAIL_ACCOUNT = "3489130766@qq.com"
EMAIL_PASSWORD = "ckrdwvywzengdbeg"  # 刚才的授权码
API_ENDPOINT = "http://127.0.0.1:8000/collect/auto"
POLL_INTERVAL = 10


# ==================================================

def decode_str(s):
    if not s: return ""
    value, charset = decode_header(s)[0]
    if charset:
        value = value.decode(charset)
    elif isinstance(value, bytes):
        value = value.decode('utf-8', errors='ignore')
    return value


def get_email_body(msg):
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                return part.get_payload(decode=True).decode('utf-8', errors='ignore')
    else:
        return msg.get_payload(decode=True).decode('utf-8', errors='ignore')
    return ""


def check_inbox():
    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        mail.select("inbox")

        status, messages = mail.search(None, "UNSEEN")
        email_ids = messages[0].split()

        if email_ids:
            print(f"📬 发现 {len(email_ids)} 封新邮件！开始处理...")

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])

                    subject = decode_str(msg.get("Subject", "No Subject"))
                    sender = decode_str(msg.get("From", "Unknown Sender"))
                    body = get_email_body(msg)

                    print(f"\n--- 正在输送: {subject} ---")

                    payload = {
                        "sender": sender,
                        "subject": subject,
                        "raw_content": body or "空邮件"
                    }

                    try:
                        res = requests.post(API_ENDPOINT, json=payload)
                        if res.status_code == 200:
                            print(f"✅ 成功送达 AI 后厨！")
                            mail.store(e_id, '+FLAGS', '\\Seen')
                        else:
                            print(f"❌ 后端退回了数据: {res.text}")
                    except Exception as e:
                        print(f"⚠️ 呼叫 FastAPI 失败: {e}")

        mail.logout()

    except Exception as e:
        print(f"❌ 监听器连接出错: {e}")


if __name__ == "__main__":
    print(f"🚀 极简测试版监听器已上线！")
    while True:
        check_inbox()
        time.sleep(POLL_INTERVAL)