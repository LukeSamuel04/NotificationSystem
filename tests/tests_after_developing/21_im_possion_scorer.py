# tests/tests_after_developing/21_test_im_poisson_scorer.py
import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.services.local_scoring.poission_urgency_scorer.im.scorer import IMPoissonUrgencyScorer
from app.models.notifications import Notification
from app.models.im_session import IMSessionState


class TestIMPoissonUrgencyScorer(unittest.TestCase):

    def setUp(self):
        self.mock_db = MagicMock()
        self.scorer = IMPoissonUrgencyScorer(self.mock_db)

        self.sender_id = "test_user_666"
        self.account_id = "101"
        self.now = datetime.now()

        # 测试全局状态变量，方便在不同测试用例中动态调整
        self.current_total_msgs = 0
        self.current_first_msg_at = self.now
        self.current_k = 0  # 最近 30 分钟发了多少条
        self.current_session_state = None

        # 🚀 核心：打造一个智能路由 Mock，它能根据 query 传入的不同模型，返回不同的假数据
        def mock_query_routing(*args):
            mock_q = MagicMock()

            # 路由 A：查 func.count 和 func.min (代表第一步的全局统计)
            if len(args) == 2 and "count" in str(args[0]):
                mock_stats = MagicMock()
                mock_stats.total_msgs = self.current_total_msgs
                mock_stats.first_msg_at = self.current_first_msg_at
                mock_q.filter.return_value.first.return_value = mock_stats

            # 路由 B：查 IMSessionState (代表档案更新)
            elif args[0] == IMSessionState:
                mock_q.filter_by.return_value.first.return_value = self.current_session_state

            # 路由 C：查 Notification (代表滑动窗口内的 k 值统计)
            elif args[0] == Notification:
                mock_q.filter.return_value.count.return_value = self.current_k

            return mock_q

        self.mock_db.query.side_effect = mock_query_routing

    def test_cold_start_interception(self):
        """【数学逻辑测试 1】冷启动防线：验证总消息数 < 20 时，绝对返回基础倍率 1.0"""
        self.current_total_msgs = 19  # 差一条越过门槛
        self.current_k = 19  # 哪怕最近半小时发了 19 条

        result = self.scorer.calculate(self.sender_id, self.account_id)

        self.assertFalse(result["is_burst_active"])
        self.assertEqual(result["poisson_probability"], 1.0)
        self.assertEqual(result["burst_factor"], 1.0)

    def test_normal_quiet_behavior(self):
        """【数学逻辑测试 2】常规静默防线：验证长期低频且当前也没有暴增时，不触发提权"""
        self.current_total_msgs = 100
        # 假设号存活了 100 个小时，平均 1小时 1条消息 (lambda=1.0)
        self.current_first_msg_at = self.now - timedelta(hours=100)
        self.current_k = 1  # 最近 30 分钟只发了 1 条

        result = self.scorer.calculate(self.sender_id, self.account_id)

        # 概率应该很高（大概率事件），不触发 burst
        self.assertTrue(result["poisson_probability"] > 0.05)
        self.assertEqual(result["burst_factor"], 1.0)

    def test_extreme_burst_detection(self):
        """【数学逻辑测试 3】极端轰炸捕获：验证长期安静的人突然狂发消息，必须获得高额加权"""
        self.current_total_msgs = 100
        # 存活 100 小时，平均 1小时 1条 (lambda=1)
        self.current_first_msg_at = self.now - timedelta(hours=100)
        # 💥 突然半小时内狂发了 15 条消息！
        self.current_k = 15

        result = self.scorer.calculate(self.sender_id, self.account_id)

        # P(X >= 15) 在 lambda = 2.0 (下限兜底值) 下，概率无限接近于 0
        self.assertTrue(result["is_burst_active"])
        self.assertTrue(result["poisson_probability"] < 0.05)
        self.assertTrue(result["burst_factor"] > 1.5)  # 倍率必须显著上升
        self.assertTrue(result["burst_factor"] <= 2.0)  # 验证封顶不超过 2.0

    def test_architectural_discipline_no_db_add(self):
        """【架构纪律测试 4】越权隔离校验：验证算子仅执行内存属性刷新，绝对没有调用 db.add 或 db.commit"""
        self.current_total_msgs = 50
        self.current_first_msg_at = self.now - timedelta(hours=10)
        self.current_k = 5

        # 模拟库里已经存在这个会话状态
        self.current_session_state = MagicMock(spec=IMSessionState)

        self.scorer.calculate(self.sender_id, self.account_id)

        # 1. 验证 historical_lambda 被正确更新了 (50条 / 10小时 ≈ 5.0)
        # 使用 assertAlmostEqual 允许小数点后 2 位的浮点数微小误差
        self.assertAlmostEqual(self.current_session_state.historical_lambda, 5.0, places=2)

        # 2. 💥 核心断言：验证绝对没有越权做数据库持久化操作！
        self.mock_db.add.assert_not_called()
        self.mock_db.commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()