# test/test_priority_orchestrator.py
import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 引入核心模型与大脑
from app.db.base_class import Base
from app.models.notifications import Notification
from app.models.im_session import IMSessionState
from app.models.user_preference import UserPreference
from app.models.analysis_payload import AnalysisPayload
from app.services.local_scoring.priority_orchestrator import PriorityOrchestrator


class TestPriorityOrchestrator(unittest.TestCase):
    def setUp(self):
        """初始化纯净的内存测试环境"""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.orchestrator = PriorityOrchestrator(self.db)
        self.acc_id = "bth_student_user"
        self.sender_id = "gymbro_insta"

        # ---------------------------------------------------------
        # 1. 注入偏好因子规则
        # ---------------------------------------------------------
        seed_rules = [
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="topic", target_value="assignment",
                           preference_factor=2.5),
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="topic", target_value="广告",
                           preference_factor=0.05),
            UserPreference(account_id=self.acc_id, platform="email",
                           preference_type="email_domain", target_value="bth.se",
                           preference_factor=1.5),
        ]
        # 2. 预置 Session 状态
        session = IMSessionState(external_sender_id=self.sender_id, account_id=self.acc_id,
                                 platform="instagram", historical_lambda=0.0)

        self.db.add_all(seed_rules + [session])
        self.db.commit()

    def tearDown(self):
        self.db.close()

    def _seed_notifications(self, sender):
        """构造真实的突发场景数据"""
        now = datetime.now()
        for i in range(30):
            msg = Notification(account_id=self.acc_id, platform="instagram",
                               account_msg_id=f"h_{i}", sender="Name",
                               external_sender_id=sender, received_at=now - timedelta(days=i + 1))
            self.db.add(msg)

        for i in range(15):
            msg = Notification(account_id=self.acc_id, platform="instagram",
                               account_msg_id=f"b_{i}", sender="Name",
                               external_sender_id=sender, received_at=now - timedelta(minutes=2))
            self.db.add(msg)
        self.db.commit()

    def test_1_instagram_cumulative_burst(self):
        """🎯 验证：突发轰炸 + 话题偏好 + 自动存入冷表"""
        self._seed_notifications(self.sender_id)

        ai_score = 6
        # 💥 修正：传入 5 个位置参数，包括新加的 notification_id
        res = self.orchestrator.resolve_priority(
            self.acc_id,
            999,  # notification_id
            self.sender_id,
            ai_score,
            "I finished the assignment"
        )

        print("\n[测试1: Instagram 复合叠加]", res)
        self.assertGreaterEqual(res["final_priority"], 9)

        # 验证冷表记录是否产生
        payload = self.db.query(AnalysisPayload).filter_by(notification_id=999).first()
        self.assertIsNotNone(payload)
        self.assertEqual(payload.analysis_data["ai_logic"]["base_score"], 6)

    def test_2_ad_suppression_with_high_freq(self):
        """🎯 验证：即使高频发送，命中广告规则也会被暴力降权"""
        self._seed_notifications("spam_bot")

        ai_score = 9
        # 💥 修正：同步更新参数顺序
        res = self.orchestrator.resolve_priority(
            self.acc_id,
            888,  # notification_id
            "spam_bot",
            ai_score,
            "这是一则超值广告"
        )

        print("\n[测试2: 广告强制降权]", res)
        self.assertLess(res["final_priority"], 5)

    def test_3_email_domain_auto_extraction(self):
        """🎯 验证：Email 场景下的自动域名提取与评分"""
        ai_score = 5
        # 💥 修正：显式使用关键字参数或遵循新顺序
        res = self.orchestrator.resolve_priority(
            account_id=self.acc_id,
            notification_id=777,
            external_sender_id="teacher@bth.se",
            ai_score=ai_score,
            current_topic="Meeting tomorrow",
            platform="email"
        )
        print("\n[测试3: Email 域自动匹配]", res)
        self.assertEqual(res["final_priority"], 6)


if __name__ == "__main__":
    unittest.main()