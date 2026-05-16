# test/tests_after_developing/2_email_scorer_real.py
import os
import unittest
import logging
from dotenv import load_dotenv, find_dotenv

# 导入打分模型与核心函数
from workers.ai.models.email.scorer import analyze_email_context, EmailAIResult

# 激活日志输出，方便在控制台肉眼观察真实的大模型原生返回
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RealEmailScorerTest")


class TestEmailScorerReal(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        """测试前置检查：确保本地 .env 环境变量已正确加载"""
        load_dotenv(find_dotenv(), override=True)
        cls.api_key = os.getenv("LLM_API_KEY")
        cls.base_url = os.getenv("LLM_BASE_URL")
        cls.model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")

        if not cls.api_key:
            raise unittest.SkipTest(
                "❌ 警告：未在环境或 .env 文件中检测到 'LLM_API_KEY'，已自动跳过真实大模型测试。"
            )

        logger.info(f"🛰️ 真实大模型测试已就绪。目标模型: {cls.model_name}, 终点站: {cls.base_url}")

    async def test_real_llm_academic_notification(self):
        """【真实测试 1】验证真实的学校/工作通知判定"""
        # 构造一个符合你日常 BTH 校园生活背景的真实剧本
        academic_script = """
        【邮件主题】: PA2552 Course Assignment Extension Confirmation
        【对话背景】: This is an academic notification from Blekinge Institute of Technology (BTH).
        【！！当前待处理邮件！！】: 
        From: course-coordinator@bth.se
        Body: Hi Luke, regarding your request for the MS1411 and PA2552 project submission deadline, we have approved a 48-hour extension. Please ensure your Selenium Page Object Model automation suite is pushed to GitHub before Friday.
        """

        logger.info("🧠 正在发送【工作学业类】邮件剧本至真实大模型...")
        result = await analyze_email_context(academic_script)

        # 断言判定：真实模型返回不能为 None，且必须能被成功转化为强类型模型
        self.assertIsNotNone(result)
        self.assertIsInstance(result, EmailAIResult)

        # 业务逻辑断言：学业分类 ID 必须为 3，分值应处于高优先区间 (通常 6-8 分)
        logger.info(
            f"✅ 真实模型返回 -> 分类: {result.category_id}, 分数: {result.priority_score}, 摘要: {result.summary}")
        self.assertEqual(result.category_id, 3)
        self.assertTrue(5 <= result.priority_score <= 9)

    async def test_real_llm_verification_code(self):
        """【真实测试 2】验证高危验证码的绝对时效性判分 (期望强卡 10 分)"""
        otp_script = """
        【邮件主题】: GitHub Password Reset OTP
        【对话背景】: Automated security enforcement system.
        【！！当前待处理邮件！！】: 
        From: noreply@github.com
        Body: [GitHub] Verification code: 834921. This code will expire in 10 minutes. If you did not request this, please secure your credentials immediately.
        """

        logger.info("🧠 正在发送【验证码类】邮件剧本至真实大模型...")
        result = await analyze_email_context(otp_script)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EmailAIResult)

        # 业务逻辑断言：验证码分类 ID 必须为 2，根据 Prompt 指令，最新验证码必须死死判定为 10 分！
        logger.info(
            f"✅ 真实模型返回 -> 分类: {result.category_id}, 分数: {result.priority_score}, 摘要: {result.summary}")
        self.assertEqual(result.category_id, 2)
        self.assertEqual(result.priority_score, 10)
        self.assertIn("834921", result.summary)

    async def test_real_llm_spam_marketing(self):
        """【真实测试 3】验证垃圾推销广告的降权熔断机制 (期望强卡 1 分)"""
        spam_script = """
        【邮件主题】: Willys Karlskrona: Superklipp på Fuet och Grillkorv!
        【对话背景】: Routine newsletter and commercial promotion.
        【！！当前待处理邮件！！】: 
        From: nyhetsbrev@willys.se
        Body: Hej! Missa inte veckans extrapriser i Karlskrona! Spanska Fuet-korvar för 15 kr, perfekt för helgens matlagning. Handla nu på Willys och spara 20%!
        """

        logger.info("🧠 正在发送【广告推销类】邮件剧本至真实大模型...")
        result = await analyze_email_context(spam_script)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, EmailAIResult)

        # 业务逻辑断言：垃圾广告分类 ID 必须为 7，根据 Prompt 指令，必须强行拦截为最底线的 1 分！
        logger.info(
            f"✅ 真实模型返回 -> 分类: {result.category_id}, 分数: {result.priority_score}, 摘要: {result.summary}")
        self.assertEqual(result.category_id, 7)
        self.assertEqual(result.priority_score, 1)


# 💥 挂载标准单元测试启动入口，在 IDE 中允许直接一键点击点击运行
if __name__ == "__main__":
    unittest.main()