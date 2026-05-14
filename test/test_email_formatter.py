# test/test_email_formatter.py
import sys
import os

# 将项目根目录加入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.context.email.formatter import EmailFormatter
from workers.notification.utils.html_cleaner import clean_html

# 模拟 1: 带有巨量 HTML 标签、内联样式和乱码的推广邮件
DIRTY_HTML_SPAM = """
<html>
<head><style>body { font-family: Arial; }</style></head>
<body>
    <div style="background-color: #f0f0f0; padding: 20px;">
        <h1 style="color: red;">Willys 周末大狂欢！</h1>
        <p>亲爱的顾客，<b>全场披萨买一送一</b>！</p>
        <img src="tracker.gif" style="display:none;" />
        <br>
        <p style="font-size: 10px; color: gray;">
            如果您不想再收到此类邮件，请点击 <a href="#unsubscribe">这里退订</a>。<br>
            Willys AB, Karlskrona, Sweden. All rights reserved.
        </p>
    </div>
</body>
</html>
"""

# 模拟 2: 带有冗长签名档和历史引用链的商务回复
DIRTY_CORPORATE_REPLY = """
Hi Luke,

The backend deployment is complete. You can test the new API now.

Best regards,

-- 
John Doe
Senior Software Engineer | AWS Cloud Team
Phone: +46 123 456 789
Email: john.doe@aws.example.com
"Building the future, one block at a time."
******************************************************************
This email and any files transmitted with it are confidential and
intended solely for the use of the individual or entity to whom they
are addressed. 
******************************************************************

On Fri, May 8, 2026 at 4:30 PM, Luke <my_test_email@example.com> wrote:
> Hi John,
> 
> Can you let me know when the backend deployment is finished? 
> We are waiting to run the integration tests.
>
> Thanks!
"""

# 💥 模拟 3: 充满恶意空格、制表符和连续换行符的脏数据
DIRTY_WHITESPACE_SPAM = """


        【Willys 本周惊喜掉落】   



             亲爱的顾客，


                     本周末所有          冷冻披萨          买一送一！





                                         快来采购吧！




"""


def run_formatter_test():
    print("🧹 开始 Email Formatter 清洗能力极限测试...\n")
    print("=" * 70)

    # --- 测试 1：纯净度测试 (HTML 剥离) ---
    print("📡 测试用例 1: HTML 促销垃圾邮件清洗")
    cleaned_spam_html = clean_html(DIRTY_HTML_SPAM)
    final_spam = EmailFormatter.extract_pure_reply(cleaned_spam_html)
    print("🔽 原始数据长度:", len(DIRTY_HTML_SPAM))
    print(f"✅ 清洗后结果:\n{final_spam}\n")
    print("-" * 70)

    # --- 测试 2：逻辑切割测试 (剔除签名和引用) ---
    print("📡 测试用例 2: 剔除商务签名档与历史引用 (Mailgun 算法测试)")
    final_reply = EmailFormatter.extract_pure_reply(DIRTY_CORPORATE_REPLY)
    print("🔽 原始数据长度:", len(DIRTY_CORPORATE_REPLY))
    print(f"✅ 清洗后结果:\n{final_reply}\n")
    print("-" * 70)

    # --- 测试 3：空白符终极压缩测试 ---
    print("📡 测试用例 3: 终极空白符与换行符压缩测试")
    # 先过一遍 html_cleaner (通常也会顺手处理一些格式)，再过 formatter
    cleaned_whitespace_html = clean_html(DIRTY_WHITESPACE_SPAM)
    final_whitespace = EmailFormatter.extract_pure_reply(cleaned_whitespace_html)

    print("🔽 原始数据长度:", len(DIRTY_WHITESPACE_SPAM))
    print(f"✅ 清洗后结果:\n{final_whitespace}\n")
    print("=" * 70)


if __name__ == "__main__":
    run_formatter_test()