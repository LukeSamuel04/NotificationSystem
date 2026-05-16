# tests/tests_after_developing/23_test_priority_orchestrator.py
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.local_scoring.priority_orchestrator import PriorityOrchestrator
from app.models.analysis_payload import AnalysisPayload
from app.models.im_session import IMSessionState


class TestPriorityOrchestrator(unittest.TestCase):

    def setUp(self):
        """挂载通用的 Mock 数据库"""
        self.mock_db = MagicMock()

    @patch("app.services.local_scoring.priority_orchestrator.UserPreferenceScorer")
    @patch("app.services.local_scoring.priority_orchestrator.IMPoissonUrgencyScorer")
    def test_instagram_platform_full_fusion_math(self, mock_poisson_cls, mock_pref_cls):
        """【数学与热更测试 1】Instagram 专线：验证平方根数学融合公式与 IMSession 热点红点点亮机制"""

        # 1. 模拟子算子返回值
        mock_poisson_inst = MagicMock()
        mock_poisson_cls.return_value = mock_poisson_inst
        mock_poisson_inst.calculate.return_value = {"burst_factor": 4.0}  # 泊松给 4.0 倍

        mock_pref_inst = MagicMock()
        mock_pref_cls.return_value = mock_pref_inst
        mock_pref_inst.calculate.return_value = {"preference_factor": 1.0}  # 偏好给 1.0 倍

        # 2. 模拟数据库查询已存在的 IMSession
        mock_im_session = MagicMock(spec=IMSessionState)
        mock_im_session.is_read = True  # 原本是已读状态
        self.mock_db.query.return_value.filter_by.return_value.first.return_value = mock_im_session

        orchestrator = PriorityOrchestrator(self.mock_db)

        # 3. 执行核心调度
        # AI 给了 3 分，数学期望：3 * sqrt(4.0 * 1.0) = 6.0 分
        result = orchestrator.resolve_priority(
            account_id="user_101",
            notification_id=999,
            external_sender_id="gymbro",
            ai_score=3,
            current_topic="Workout",
            platform="instagram"
        )

        # 4. 断言判定：
        # 验证数学精度
        self.assertEqual(result["final_priority"], 6)

        # 验证冷表落盘：AnalysisPayload 是否被正确组装
        self.mock_db.add.assert_called_once()
        added_payload = self.mock_db.add.call_args[0][0]
        self.assertIsInstance(added_payload, AnalysisPayload)
        self.assertEqual(added_payload.analysis_data["behavioral_features"]["combined_multiplier"], 2.0)

        # 💥 验证热表更新与红点唤醒：
        self.assertEqual(mock_im_session.priority_score, 6)
        self.assertEqual(mock_im_session.current_topic, "Workout")
        self.assertFalse(mock_im_session.is_read)  # 必须被强制点亮红点 (is_read=False)

    @patch("app.services.local_scoring.priority_orchestrator.UserPreferenceScorer")
    @patch("app.services.local_scoring.priority_orchestrator.IMPoissonUrgencyScorer")
    def test_email_platform_domain_extraction(self, mock_poisson_cls, mock_pref_cls):
        """【隔离测试 2】Email 专线：验证 Email 平台不调用泊松算法，且精准提取 domain 后缀"""

        mock_poisson_inst = MagicMock()
        mock_poisson_cls.return_value = mock_poisson_inst

        mock_pref_inst = MagicMock()
        mock_pref_cls.return_value = mock_pref_inst
        # 假设域名偏好触发，给了 2.25 倍加成
        mock_pref_inst.calculate.return_value = {"preference_factor": 2.25}

        orchestrator = PriorityOrchestrator(self.mock_db)

        # AI 给了 4 分，数学期望：4 * sqrt(1.0 * 2.25) = 4 * 1.5 = 6.0 分
        result = orchestrator.resolve_priority(
            account_id="user_102",
            notification_id=888,
            external_sender_id="teacher@bth.se",  # 包含域名
            ai_score=4,
            current_topic="Homework",
            platform="email"
        )

        # 验证数学精度
        self.assertEqual(result["final_priority"], 6)

        # 验证泊松算子是否被严格隔离（不准给 Email 算泊松）
        mock_poisson_inst.calculate.assert_not_called()

        # 💥 验证域名自动切片逻辑：必须准确提取出 "bth.se" 并喂给偏好算子
        mock_pref_inst.calculate.assert_called_once_with(
            account_id="user_102",
            platform="email",
            sender_id="teacher@bth.se",
            current_topic="Homework",
            email_domain="bth.se"  # 域切片正确
        )

        # 验证热表隔离（不准去查询或更新 IMSessionState）
        self.mock_db.query.assert_not_called()

    @patch("app.services.local_scoring.priority_orchestrator.UserPreferenceScorer")
    @patch("app.services.local_scoring.priority_orchestrator.IMPoissonUrgencyScorer")
    def test_score_clamping_boundaries(self, mock_poisson_cls, mock_pref_cls):
        """【极端边界测试 3】1-10 分防溢出装甲：验证极其离谱的乘数也不会击穿 1-10 分的界限"""

        mock_poisson_inst = MagicMock()
        mock_poisson_cls.return_value = mock_poisson_inst
        mock_pref_inst = MagicMock()
        mock_pref_cls.return_value = mock_pref_inst

        orchestrator = PriorityOrchestrator(self.mock_db)

        # 案例 A：突破上限天花板
        # AI给满分10，泊松和偏好给了极其夸张的 100 倍率
        mock_poisson_inst.calculate.return_value = {"burst_factor": 10.0}
        mock_pref_inst.calculate.return_value = {"preference_factor": 10.0}

        res_high = orchestrator.resolve_priority("a1", 1, "s1", ai_score=10, current_topic="t", platform="instagram")
        self.assertEqual(res_high["final_priority"], 10)  # 绝不能是 100 分，必须被按死在 10 分

        # 案例 B：击穿下限地板
        # AI 给 1 分，被垃圾邮件偏好规则打压到 0.01 倍率
        mock_poisson_inst.calculate.return_value = {"burst_factor": 1.0}
        mock_pref_inst.calculate.return_value = {"preference_factor": 0.01}

        res_low = orchestrator.resolve_priority("a2", 2, "s2", ai_score=1, current_topic="t", platform="instagram")
        self.assertEqual(res_low["final_priority"], 1)  # 算出来是 0.1 分，但必须被兜底抬高到 1 分


if __name__ == "__main__":
    unittest.main()