# test/test_priority_orchestrator_extreme.py
import unittest
import uuid  # 💥 引入 UUID 保证 ID 唯一
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.models.notifications import Notification
from app.models.im_session import IMSessionState
from app.models.user_preference import UserPreference
from app.models.analysis_payload import AnalysisPayload  # 💥 引入冷表模型确保建表完整
from app.services.local_scoring.priority_orchestrator import PriorityOrchestrator


class TestPriorityStress(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.orchestrator = PriorityOrchestrator(self.db)
        self.acc_id = "stress_test_user"
        self.sender_id = "target_contact"

        rules = [
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="sender_id", target_value="professor_lucas",
                           preference_factor=5.0),
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="topic", target_value="urgent",
                           preference_factor=2.0),
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="topic", target_value="assignment",
                           preference_factor=2.0),
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="topic", target_value="promotion",
                           preference_factor=0.0),
        ]
        self.db.add_all(rules)
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _seed_history(self, count, sender, is_burst=False):
        """修正版数据灌入：使用随机 UUID 保证 account_msg_id 绝不冲突"""
        now = datetime.now()
        for i in range(count):
            unique_id = f"m_{uuid.uuid4().hex[:8]}_{sender}"
            ts = now - timedelta(minutes=2) if is_burst else now - timedelta(days=i + 1)

            msg = Notification(
                account_id=self.acc_id,
                platform="instagram",
                account_msg_id=unique_id,
                sender="Test",
                external_sender_id=sender,
                received_at=ts,
                status="pending",
                is_from_me=0
            )
            self.db.add(msg)
        self.db.commit()

    def test_4_cold_start_stability(self):
        """🎯 冷启动防线测试"""
        self._seed_history(15, "new_stranger", is_burst=True)
        # 💥 适配完整入参签名：显式补充传入测试专用的 notification_id 占位符
        res = self.orchestrator.resolve_priority(
            account_id=self.acc_id,
            notification_id=1001,
            external_sender_id="new_stranger",
            ai_score=5,
            current_topic="Hello"
        )
        print("\n[压力测试: 冷启动防线]", res)
        # 💥 修正断言键值映射层级，严格对齐冷表特征快照字典
        self.assertEqual(res["analysis_snapshot"]["behavioral_features"]["poisson_factor"], 1.0)

    def test_5_multiple_factor_stacking(self):
        """🎯 话题因子累乘测试"""
        res = self.orchestrator.resolve_priority(
            account_id=self.acc_id,
            notification_id=1002,
            external_sender_id="friend",
            ai_score=4,
            current_topic="Urgent assignment help"
        )
        print("\n[压力测试: 话题叠加提权]", res)
        # sqrt(2.0 * 2.0) = 2.0 -> 4 * 2.0 = 8
        self.assertEqual(res["final_priority"], 8)

    def test_6_zero_factor_blackhole(self):
        """🎯 零分降权拦截测试"""
        res = self.orchestrator.resolve_priority(
            account_id=self.acc_id,
            notification_id=1003,
            external_sender_id="spammer",
            ai_score=10,
            current_topic="Special promotion for you"
        )
        print("\n[压力测试: 零分黑洞拦截]", res)
        self.assertEqual(res["final_priority"], 1)

    def test_7_extreme_multiplier_safety(self):
        """🎯 极限因子封顶测试：验证非线性平方根放缩"""
        self._seed_history(30, "professor_lucas")
        self._seed_history(15, "professor_lucas", is_burst=True)

        res = self.orchestrator.resolve_priority(
            account_id=self.acc_id,
            notification_id=1004,
            external_sender_id="professor_lucas",
            ai_score=3,
            current_topic="Urgent news"
        )
        print("\n[压力测试: 极限因子封顶]", res)
        self.assertEqual(res["final_priority"], 10)

        # 验证冷数据记录表成功落盘快照
        payload_count = self.db.query(AnalysisPayload).count()
        self.assertGreaterEqual(payload_count, 1)


if __name__ == "__main__":
    unittest.main()