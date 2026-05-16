# tests/tests_after_developing/1_e2e_pipeline_integration.py
import unittest
import asyncio
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import sys
import os

# 将项目根目录加入路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 引入真实的 SQLAlchemy 引擎和基类
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.base_class import Base

# 引入你的真实 ORM 模型
from app.models.account import FetchAccount
from app.models.notifications import Notification
from app.models.notification_payloads import NotificationPayload
from app.models.im_session import IMSessionState
from app.models.user_preference import UserPreference
from app.models.email_analysis import EmailAnalysis
from app.models.analysis_payload import AnalysisPayload

# 引入待测试的真实执行器
from workers.ai.managers.email_executor import process_pending_emails
from workers.ai.managers.im_executor import process_pending_im_sessions


class TestE2EFullPipeline(unittest.IsolatedAsyncioTestCase):

    @classmethod
    def setUpClass(cls):
        """【全局准备】在内存中创建一个纯净的、真实的 SQLite 数据库"""
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False}
        )
        cls.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)
        Base.metadata.create_all(bind=cls.engine)

    @classmethod
    def tearDownClass(cls):
        """【全局收尾】销毁内存数据库"""
        Base.metadata.drop_all(bind=cls.engine)

    def setUp(self):
        """每个测试用例前：开启独立的 DB Session，并注入基础测试数据"""
        self.db = self.TestingSessionLocal()

        # 1. 注入一个合法的接收账号
        self.test_account = FetchAccount(
            id=999, platform="email", platform_account_id="test_platform_999",
            username="master@bth.se", config={"env": "e2e_test"}
        )
        self.db.add(self.test_account)
        self.db.commit()

    def tearDown(self):
        """每个测试用例后：清空表数据，防止互相干扰"""
        for table in reversed(Base.metadata.sorted_tables):
            self.db.execute(table.delete())
        self.db.commit()
        self.db.close()

    @patch("workers.ai.managers.email_executor.analyze_email_context", new_callable=AsyncMock)
    @patch("workers.ai.managers.email_executor.get_email_formatted_context", new_callable=AsyncMock)
    async def test_e2e_email_pipeline_with_math_verification(self, mock_context, mock_ai):
        """【全链路 E2E 1】Email 极压融合算分：验证多规则命中时，AI分数与平方根平滑公式的真实落盘结果"""

        rule_domain = UserPreference(account_id="999", platform="email", preference_type="email_domain",
                                     target_value="bth.se", preference_factor=2.0)
        rule_topic = UserPreference(account_id="999", platform="global", preference_type="topic", target_value="urgent",
                                    preference_factor=3.0)
        self.db.add_all([rule_domain, rule_topic])
        self.db.commit()

        msg = Notification(
            account_id=999, platform="email", account_msg_id="msg_1",
            sender="Professor", external_sender_id="prof@bth.se",
            subject="URGENT: Project deadline",
            cleaned_content="This is email content", status="pending", received_at=datetime.now()
        )
        self.db.add(msg)
        self.db.commit()

        mock_context.return_value = "Context"

        mock_ai_result = AsyncMock()
        mock_ai_result.priority_score = 4
        mock_ai_result.summary = "urgent project deadline discussion"
        mock_ai_result.category_id = 101
        mock_ai.return_value = mock_ai_result

        processed_count = await process_pending_emails(self.db)
        self.assertEqual(processed_count, 1)

        analysis = self.db.query(EmailAnalysis).first()
        self.assertEqual(analysis.priority_score, 10)

    @patch("workers.ai.managers.im_executor.analyze_social_media_session", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_executor.get_formatted_context", new_callable=AsyncMock)
    async def test_e2e_im_pipeline_burst_poisson(self, mock_context, mock_ai):
        """【全链路 E2E 2】IM 泊松轰炸：模拟短时间涌入海量消息，验证真实数据库下泊松衰减与冷热表双写"""

        self.test_account.platform = "instagram"
        self.db.commit()

        now = datetime.now()

        # 🚀 核心修复：建立10小时的长线时间纵深背景噪音
        # 灌入 20 条“历史已读消息”，拉低历史均值基线 (20条/10小时 = 2条/小时)
        history_start = now - timedelta(hours=10)
        historical_msgs = []
        for i in range(20):
            historical_msgs.append(Notification(
                account_id=999, platform="instagram", account_msg_id=f"ig_hist_{i}",
                sender="Crazy Ex", external_sender_id="ex_user_001",
                cleaned_content="Old regular message", status="processed",  # 标记为已处理
                received_at=history_start + timedelta(minutes=i * 30)
            ))
        self.db.add_all(historical_msgs)
        self.db.commit()

        # 🚀 紧接着，在最近 2 分钟内瞬间倾泻 25 条极速轰炸未读消息！
        burst_msgs = []
        for i in range(25):
            burst_msgs.append(Notification(
                account_id=999, platform="instagram", account_msg_id=f"ig_burst_{i}",
                sender="Crazy Ex", external_sender_id="ex_user_001",
                cleaned_content="Reply me right now!!!", status="pending",  # 待办状态
                received_at=now - timedelta(seconds=i * 4)
            ))
        self.db.add_all(burst_msgs)
        self.db.commit()

        mock_context.return_value = "Context"

        mock_ai_result = AsyncMock()
        mock_ai_result.priority_score = 3
        mock_ai_result.current_topic = "Spamming"
        mock_ai_result.summary_snapshot = "User sending rapid messages"
        mock_ai.return_value = mock_ai_result

        # 执行单次扫盘
        processed_count = await process_pending_im_sessions(self.db)
        self.assertEqual(processed_count, 1)

        session_state = self.db.query(IMSessionState).first()
        self.assertIsNotNone(session_state)
        self.assertFalse(session_state.is_read)

        # 🔥 此时基线极低（半小时本应只有1条），却突然涌入25条！泊松公式瞬间引爆，触发超级提权！
        self.assertTrue(session_state.priority_score > 3)

        payload = self.db.query(AnalysisPayload).first()
        self.assertIsNotNone(payload)
        self.assertTrue(payload.analysis_data["behavioral_features"]["poisson_factor"] > 1.2)

    @patch("workers.ai.managers.im_executor.analyze_social_media_session", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_executor.get_formatted_context", new_callable=AsyncMock)
    async def test_e2e_im_echo_downgrade_handling(self, mock_context, mock_ai):
        """【全链路 E2E 3】回声降权防线：深度模拟 Webhook 收到自己发出的消息时，AI降权闭环测试"""

        self.test_account.platform = "instagram"
        self.db.commit()

        now = datetime.now()
        incoming_msg = Notification(
            account_id=999, platform="instagram", account_msg_id="ig_incoming_1",
            sender="Client", external_sender_id="client_001", is_from_me=False,
            cleaned_content="The server is on fire!", status="pending", received_at=now - timedelta(minutes=5)
        )
        self.db.add(incoming_msg)
        self.db.commit()

        echo_msg = Notification(
            account_id=999, platform="instagram", account_msg_id="ig_echo_1",
            sender="Me", external_sender_id="client_001", is_from_me=True,
            cleaned_content="I am fixing it now.", status="pending", received_at=now
        )
        self.db.add(echo_msg)
        self.db.commit()

        mock_context.return_value = "Client: The server is on fire! \n Me: I am fixing it now."

        mock_ai_result = AsyncMock()
        mock_ai_result.priority_score = 1
        mock_ai_result.current_topic = "Server fixing"
        mock_ai_result.summary_snapshot = "Already replied and acknowledged"
        mock_ai.return_value = mock_ai_result

        processed_count = await process_pending_im_sessions(self.db)
        self.assertEqual(processed_count, 1)

        session_state = self.db.query(IMSessionState).filter_by(external_sender_id="client_001").first()
        self.assertIsNotNone(session_state)
        self.assertEqual(session_state.priority_score, 1)
        self.assertEqual(session_state.current_topic, "Server fixing")

        pending_count = self.db.query(Notification).filter_by(status="pending").count()
        self.assertEqual(pending_count, 0)


if __name__ == "__main__":
    unittest.main()