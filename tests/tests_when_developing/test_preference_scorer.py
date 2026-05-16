# test/test_user_preference_scorer.py
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 引入基础 Base 和相关模型
from app.db.base_class import Base
from app.models.user_preference import UserPreference

# 引入核心算子
from app.services.local_scoring.user_preference_scorer.scorer import UserPreferenceScorer


class TestUserPreferenceScorer(unittest.TestCase):
    def setUp(self):
        """
        每次测试前：初始化内存数据库并注入模拟规则数据
        """
        # 使用内存 SQLite 保证环境纯净
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.scorer = UserPreferenceScorer(self.db)
        self.acc_id = "test_user_bth"

        # ---------------------------------------------------------
        # 预置种子数据 (Seed Data)
        # ---------------------------------------------------------
        seed_rules = [
            # 1. Instagram 特定发件人提权 (Gymbro)
            UserPreference(
                account_id=self.acc_id, platform="instagram",
                preference_type="sender_id", target_value="gymbro_001",
                preference_factor=1.5
            ),
            # 2. 全局话题规则：广告降权 (Factor = 0.1)
            UserPreference(
                account_id=self.acc_id, platform="global",
                preference_type="topic", target_value="广告",
                preference_factor=0.1
            ),
            # 3. 全局话题规则：作业提权 (Factor = 2.0)
            UserPreference(
                account_id=self.acc_id, platform="global",
                preference_type="topic", target_value="assignment",
                preference_factor=2.0
            ),
            # 4. Email 专属域规则：BTH 内部邮件 (Factor = 1.2)
            UserPreference(
                account_id=self.acc_id, platform="email",
                preference_type="email_domain", target_value="bth.se",
                preference_factor=1.2
            )
        ]
        self.db.add_all(seed_rules)
        self.db.commit()

    def tearDown(self):
        """销毁内存数据库环境"""
        self.db.close()

    def test_1_instagram_single_match(self):
        """🎯 场景：普通朋友发来普通消息 (预期因子 1.0)"""
        res = self.scorer.calculate(
            account_id=self.acc_id, platform="instagram",
            sender_id="common_friend", current_topic="你好呀"
        )
        print("\n[场景1] 普通 IM:", res)
        self.assertEqual(res["preference_factor"], 1.0)

    def test_2_instagram_cumulative_multiplication(self):
        """🎯 场景：健身伙伴发来关于“assignment”的消息 (预期累乘 1.5 * 2.0 = 3.0)"""
        res = self.scorer.calculate(
            account_id=self.acc_id, platform="instagram",
            sender_id="gymbro_001", current_topic="帮我看看这个 assignment"
        )
        print("\n[场景2] 叠加态 IM:", res)
        # 验证累乘逻辑
        self.assertAlmostEqual(res["preference_factor"], 3.0)
        self.assertEqual(len(res["matched_rules"]), 2)

    def test_3_ad_suppression(self):
        """🎯 场景：检测到广告话题 (预期降权 0.1)"""
        res = self.scorer.calculate(
            account_id=self.acc_id, platform="instagram",
            sender_id="unknown_brand", current_topic="这里有超值广告优惠"
        )
        print("\n[场景3] 广告降权:", res)
        self.assertEqual(res["preference_factor"], 0.1)

    def test_4_email_domain_match(self):
        """🎯 场景：来自 BTH 的校内邮件 (预期提权 1.2)"""
        res = self.scorer.calculate(
            account_id=self.acc_id, platform="email",
            email_domain="bth.se", current_topic="课程通知"
        )
        print("\n[场景4] 域匹配 Email:", res)
        self.assertEqual(res["preference_factor"], 1.2)


if __name__ == "__main__":
    unittest.main()