# test/test_email_scorer.py
import asyncio
import sys
import os

# 将项目根目录加入路径，确保能导入 app 和 workers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.ai.models.email.scorer import analyze_email_context

# --- 虚构的测试数据上下文 (严格按照 formatter.py 生成的格式) ---

# 场景 1: 验证码 (分类 2，期望评分: 10，摘要极简)
CONTEXT_OTP = """
【邮件主题: GitHub 登录验证码】

【！！当前待处理邮件 (LATEST MESSAGE)！！】
发件人: GitHub <noreply@github.com>
时间: 2026-05-09 10:00
正文诉求:
Here is your GitHub authentication code: 847291. It expires in 10 minutes.
"""

# 场景 2: 紧急告警 (分类 1，期望评分: 9-10)
CONTEXT_URGENT_ALERT = """
【邮件主题: 🚨 [ALARM] 生产环境数据库 CPU 超过 95%】

【！！当前待处理邮件 (LATEST MESSAGE)！！】
发件人: AWS CloudWatch
时间: 2026-05-09 03:00
正文诉求:
Your RDS instance db-production has exceeded the 95% CPU utilization threshold. Immediate action required to prevent downtime.
"""

# 场景 3: 学业与工作 (分类 3，期望评分: 中高)
CONTEXT_STUDY = """
【邮件主题: MS1411 - 统计学期末项目更新】

【！！当前待处理邮件 (LATEST MESSAGE)！！】
发件人: 教授
时间: 2026-05-09 11:00
正文诉求:
同学们，MS1411课程的期末项目截止日期已提前至下周三。请务必检查你们的贝叶斯定理推导部分。
"""

# 场景 4: 垃圾与推销 (分类 7，期望评分: 1，摘要极简)
CONTEXT_SPAM = """
【邮件主题: Willys 本周特惠 - 披萨买一送一！】

【！！当前待处理邮件 (LATEST MESSAGE)！！】
发件人: Willys Plus
时间: 2026-05-08 14:00
正文诉求:
亲爱的顾客，本周末所有冷冻披萨买一送一，快来采购吧！
"""

# 场景 5: 已回复场景 (分类随意，但期望评分被强制压到 1-3)
CONTEXT_ALREADY_REPLIED = """
【邮件主题: Re: 周末训练计划】

【对话背景 (Context)】
[2026-05-08 18:00] 发件人: 周末去健身房吗？冲一下 160kg 硬拉？
----------------------------------------

【！！当前待处理邮件 (LATEST MESSAGE)！！】
发件人: 我
时间: 2026-05-08 18:05
正文诉求:
没问题，周六下午两点见，我带上腰带。
"""


async def run_test():
    test_cases = [
        ("【高优测试】登录验证码 (OTP)", CONTEXT_OTP),
        ("【高优测试】服务器宕机报警", CONTEXT_URGENT_ALERT),
        ("【常规测试】大学课程通知", CONTEXT_STUDY),
        ("【低优测试】超市打折推销", CONTEXT_SPAM),
        ("【规则测试】我已主动回复的消息", CONTEXT_ALREADY_REPLIED),
    ]

    print("🧪 开始 Email Scorer 单元测试 (基于 7 维分类法)...\n")
    print("=" * 60)

    for name, context in test_cases:
        print(f"📡 正在测试: {name}")

        result = await analyze_email_context(context)

        if result:
            print(f"✅ AI 解析成功:")
            print(f"   🗂️ 分类 ID (Category): {result.category_id}")
            print(f"   🔥 紧急评分 (Priority): {result.priority_score}/10")
            print(f"   📝 智能摘要 (Summary): {result.summary}")
        else:
            print(f"❌ AI 响应失败或 Schema 验证不通过。")

        print("-" * 60)


if __name__ == "__main__":
    asyncio.run(run_test())