# test/test_im_poisson_scorer.py
import unittest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 引入基础 Base 和相关模型
from app.db.base_class import Base
from app.models.notifications import Notification
from app.models.im_session import IMSessionState

# 🎯 核心修正：绝对对齐当前项目的底层真实物理路径
from app.services.local_scoring.poission_urgency_scorer.im.scorer import IMPoissonUrgencyScorer


class TestIMPoissonUrgencyScorer(unittest.TestCase):
    def setUp(self):
        """
        每次测试前：初始化纯净的内存 SQLite 数据库，做到绝对的测试隔离
        """
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        self.scorer = IMPoissonUrgencyScorer(self.db)
        self.sender_id = "insta_user_999"
        self.account_id = "my_system_acc_1"

    def tearDown(self):
        """测试结束后销毁会话"""
        self.db.close()

    def _seed_messages(self, timestamps):
        """辅助函数：快速向数据库灌入指定时间戳的消息队列"""
        for i, ts in enumerate(timestamps):
            msg = Notification(
                account_id=self.account_id,
                platform="instagram",
                account_msg_id=f"msg_{i}",
                sender="TestUser",
                external_sender_id=self.sender_id,
                status="processed",
                is_from_me=0,
                received_at=ts
            )
            self.db.add(msg)
        self.db.commit()

    def test_1_cold_start_interception(self):
        """🎯 测试场景一：冷启动防线验证 (样本数不足 20 条强制静默)"""
        now = datetime.now()
        # 仅灌入 5 条消息
        timestamps = [now - timedelta(days=1)] * 5
        self._seed_messages(timestamps)

        res = self.scorer.calculate(self.sender_id, self.account_id)

        print("\n[测试一输出] 冷启动状态:", res)
        self.assertFalse(res["is_burst_active"])
        self.assertEqual(res["burst_factor"], 1.0)

    def test_2_peaceful_traffic(self):
        """🎯 测试场景二：平稳佛系聊天 (基线正常，近期无突发，因子维持 1.0)"""
        now = datetime.now()
        # 过去 10 天每天发 3 条，总计 30 条 (跨越冷启动)
        timestamps = []
        for day in range(10):
            timestamps.extend([now - timedelta(days=day, hours=1)] * 3)
        self._seed_messages(timestamps)

        res = self.scorer.calculate(self.sender_id, self.account_id)

        print("\n[测试二输出] 平稳态输出:", res)
        self.assertTrue(res["is_burst_active"])
        # 既然近期 30 分钟内无极其密集的消息，因子理应按兵不动
        self.assertEqual(res["burst_factor"], 1.0)

    def test_3_extreme_burst_happen(self):
        """🎯 测试场景三：极限连环轰炸触发提权"""
        now = datetime.now()
        # 先垫入 20 条历史消息作为平稳基线 (分布在过去 5 天)
        timestamps = [now - timedelta(days=d) for d in range(1, 21)]

        # 💥 突然在过去 5 分钟内，连续轰炸 12 条消息！
        timestamps.extend([now - timedelta(minutes=2)] * 12)
        self._seed_messages(timestamps)

        res = self.scorer.calculate(self.sender_id, self.account_id)

        print("\n[测试三输出] 连环轰炸输出:", res)
        self.assertTrue(res["is_burst_active"])
        self.assertLess(res["poisson_probability"], 0.05)
        self.assertGreater(res["burst_factor"], 1.0)  # 成功提权！

    def test_4_sliding_window_expiration(self):
        """🎯 测试场景四：动态窗口精确滑动衰减验证"""
        now = datetime.now()
        # 垫入 20 条基础消息跨越冷启动
        timestamps = [now - timedelta(days=d) for d in range(1, 21)]

        # 假设 35 分钟前发生了一次 10 条的轰炸 (刚好滑出 30 分钟监测界限)
        timestamps.extend([now - timedelta(minutes=35)] * 10)
        self._seed_messages(timestamps)

        res = self.scorer.calculate(self.sender_id, self.account_id)

        print("\n[测试四输出] 窗口滑动过滤输出:", res)
        self.assertTrue(res["is_burst_active"])
        # 既然轰炸发生在 35 分钟前，当前 30 分钟窗口内的 k 应当为 0，因子安全回退到 1.0
        self.assertEqual(res["burst_factor"], 1.0)


if __name__ == "__main__":
    unittest.main()