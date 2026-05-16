# tests/tests_after_developing/3_im_scorer.py
import os
import unittest
import logging
from dotenv import load_dotenv, find_dotenv

# 导入 IM 核心分析打分函数与返回 Schema
from workers.ai.models.social_media.scorer import analyze_social_media_session
from app.schemas.im_session import IMSessionAIResult

# 配置日志，以便在控制台肉眼直观观察真实大模型吐出的原始 JSON 和分析进展
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RealIMScorerTest")


class TestIMScorerReal(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        """测试前置环境检测：确保本地 .env 的大模型网关已被加载"""
        load_dotenv(find_dotenv(), override=True)
        cls.api_key = os.getenv("LLM_API_KEY")
        cls.base_url = os.getenv("LLM_BASE_URL")
        cls.model_name = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")

        if not cls.api_key:
            raise unittest.SkipTest(
                "❌ 警告：未检测到有效 'LLM_API_KEY'，已自动跳过真实 IM 大模型集成测试。"
            )

        logger.info(f"🛰️ 真实 IM 大模型算分集成测试启动。目标模型: {cls.model_name}")

    async def test_real_im_emergency_request(self):
        """【真实测试 1】验证：突发紧急事件/高危求助（期望判定为 9-10 极高分）"""
        # 剧本设计：对方遭遇突发紧急情况，等待我方救援或重要回应
        emergency_chat_script = """
        [2026-05-15 17:10:00] 联系人 (Gymbro): Luke! Are you still at the gym or school? 
        [2026-05-15 17:10:30] 联系人 (Gymbro): I had a minor motorcycle accident near Willys Karlskrona just now. The bike freehub got locked up and I slid out. 
        [2026-05-15 17:11:15] 联系人 (Gymbro): My leg is scraped up badly, can you come over with a first-aid kit or grab me? Waiting for your reply ASAP!
        """

        logger.info("🧠 正在发送【突发求助类】聊天剧本至真实大模型...")
        result = await analyze_social_media_session(emergency_chat_script)

        # 断言：模型必须返回强类型，不准产生反序列化撕裂
        self.assertIsNotNone(result)
        self.assertIsInstance(result, IMSessionAIResult)

        logger.info(
            f"✅ 真实返回 -> 话题: {result.current_topic} | 分数: {result.priority_score} | 摘要: {result.summary_snapshot}")

        # 业务逻辑断言：此类危急情况必须触发高权惩罚因子，强制处于 9-10 的高危段
        self.assertTrue(9 <= result.priority_score <= 10)
        self.assertIn("Gymbro", result.summary_snapshot)

    async def test_real_im_academic_discussion(self):
        """【真实测试 2】验证：日常学业探讨/普通约会讨论（期望判定为 6-8 中高分）"""
        # 剧本设计：同学之间正常的学术课业和代码探讨，具有一定时效性但不必秒回
        academic_chat_script = """
        [2026-05-15 16:30:00] 联系人 (BTH Classmate): Hej Luke, are you working on the PA2552 assignment right now?
        [2026-05-15 16:31:20] 联系人 (BTH Classmate): I'm having trouble with the Selenium Page Object Model architecture. My test cases keep failing due to edge-touch sensitivity rendering latency on the mobile UI simulator.
        [2026-05-15 16:32:00] 联系人 (BTH Classmate): Do we need to push the refactored branch before the deadline or is the main branch enough? Let me know when you see this.
        """

        logger.info("🧠 正在发送【日常课业类】聊天剧本至真实大模型...")
        result = await analyze_social_media_session(academic_chat_script)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, IMSessionAIResult)

        logger.info(
            f"✅ 真实返回 -> 话题: {result.current_topic} | 分数: {result.priority_score} | 摘要: {result.summary_snapshot}")

        # 业务逻辑断言：普通咨询问题应稳稳卡在中等分数段
        self.assertTrue(6 <= result.priority_score <= 8)

    async def test_real_im_ball_in_other_court(self):
        """【真实测试 3】核心边界验证：当我方已做出最后回复时，触发熔断降权（期望强卡 1-3 极低分）"""
        # 剧本设计：虽然话题和前面很像，但最后一句是“我”发的，代表球在对方半场，当前会话完结
        ball_in_other_court_script = """
        [2026-05-15 15:00:00] 联系人 (Friend): Hey, do you want to grab some Thai chicken curry for dinner tonight near the campus?
        [2026-05-15 15:01:30] 我 (Me): That sounds amazing! I just finished my powerlifting PPL split session.
        [2026-05-15 15:02:00] 我 (Me): Let's meet at the restaurant at 19:00. I'll see you there!
        """

        logger.info("🧠 正在发送【我方已回绝/球在对方半场】边界剧本至真实大模型...")
        result = await analyze_social_media_session(ball_in_other_court_script)

        self.assertIsNotNone(result)
        self.assertIsInstance(result, IMSessionAIResult)

        logger.info(
            f"✅ 真实返回 -> 话题: {result.current_topic} | 分数: {result.priority_score} | 摘要: {result.summary_snapshot}")

        # 业务逻辑断言：由于满足 Prompt 的特殊对齐熔断指令（我方是最后发信人），分数必须坠落到 1-3 分！
        self.assertTrue(1 <= result.priority_score <= 3)


# 💥 挂载标准单元测试启动飞轮，允许在 IDE 内部一键点击点击运行
if __name__ == "__main__":
    unittest.main()