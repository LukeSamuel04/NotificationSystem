# test/test_im_scheduler_with_orchestrator.py
import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 引入项目基础层与底层数据模型
from app.db.base_class import Base
from app.models.notifications import Notification
from app.models.im_session import IMSessionState
from app.models.user_preference import UserPreference
from app.models.analysis_payload import AnalysisPayload
from app.models.account import FetchAccount
from workers.ai.managers.im_executor import process_pending_im_sessions


class TestIMSchedulerIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # 💥 核心归一化：全域严格采用纯字符串字面量，彻底杜绝主键拓扑排序崩溃
        self.acc_id = "2001"
        self.sender_id = "target_gymbro_001"

        rules = [
            UserPreference(account_id=self.acc_id, platform="instagram",
                           preference_type="topic", target_value="assignment", preference_factor=2.5),
            UserPreference(account_id=self.acc_id, platform="global",
                           preference_type="topic", target_value="广告", preference_factor=0.0)
        ]

        # 注入绝对匹配物理约束的系统账号凭证
        valid_account = FetchAccount(
            id=self.acc_id,
            platform_account_id="insta_raw_node_8899",
            platform="instagram",
            username="luke_insta_agent",
            config="{}",
            is_valid=1,
            is_active=1
        )
        self.db.add(valid_account)
        self.db.add_all(rules)
        self.db.commit()

    async def asyncTearDown(self):
        self.db.close()

    def _seed_msg(self, text, sender=None, acc_id=None, is_pending=True):
        msg = Notification(
            account_id=acc_id or self.acc_id,
            platform="instagram",
            account_msg_id=f"msg_{uuid.uuid4().hex[:8]}",
            external_sender_id=sender or self.sender_id,
            cleaned_content=text,
            status="pending" if is_pending else "processed",
            received_at=datetime.now()
        )
        self.db.add(msg)
        self.db.commit()
        return msg

    @patch("workers.ai.managers.im_executor.analyze_social_media_session", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_executor.get_formatted_context", new_callable=AsyncMock)
    async def test_1_im_full_chain_extreme_stacking(self, mock_context, mock_ai):
        """🎯 压力用例：高频突发 + 偏好叠加 -> 验证平方根放缩极值保护与冷数据存证精度"""
        for i in range(40):
            self.db.add(Notification(
                account_id=self.acc_id, platform="instagram",
                account_msg_id=f"hist_{i}", external_sender_id=self.sender_id,
                status="processed", received_at=datetime.now() - timedelta(days=i + 1)
            ))
        self.db.commit()

        target_msg = self._seed_msg("Urgent update on the assignment structure.")

        mock_ai.return_value = type('obj', (object,), {
            'priority_score': 7,
            'current_topic': 'assignment integration',
            'summary_snapshot': 'Critical code review requested.'
        })
        mock_context.return_value = "Mocked chat stream context."

        processed_count = await process_pending_im_sessions(self.db)
        self.assertEqual(processed_count, 1)

        session = self.db.query(IMSessionState).filter_by(external_sender_id=self.sender_id).first()
        self.assertEqual(session.priority_score, 10)

        payload = self.db.query(AnalysisPayload).filter_by(notification_id=target_msg.id).first()
        self.assertIsNotNone(payload)
        self.assertEqual(payload.analysis_data["behavioral_features"]["preference_factor"], 2.5)

    @patch("workers.ai.managers.im_executor.analyze_social_media_session", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_executor.get_formatted_context", new_callable=AsyncMock)
    async def test_2_im_blackhole_suppression(self, mock_context, mock_ai):
        """🎯 极端用例：黑洞词汇拦截 -> 验证零值因子对高分判定的暴力降权效力"""
        self._seed_msg("点击链接领取全额免费广告大礼包！")

        mock_ai.return_value = type('obj', (object,), {
            'priority_score': 10, 'current_topic': '违规广告推送', 'summary_snapshot': 'Spam content.'
        })
        mock_context.return_value = "Spam context."

        await process_pending_im_sessions(self.db)

        session = self.db.query(IMSessionState).filter_by(external_sender_id=self.sender_id).first()
        self.assertEqual(session.priority_score, 1)

    @patch("workers.ai.managers.im_executor.analyze_social_media_session", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_executor.get_formatted_context", new_callable=AsyncMock)
    async def test_3_im_invalid_account_interception(self, mock_context, mock_ai):
        """🎯 边界用例：非法账号越权请求 -> 验证防线成功拦截且完全避免消耗后续 AI 算力"""
        # 严格传入纯字符串格式越权标识
        self._seed_msg("Hello stranger", acc_id="9999")

        processed_count = await process_pending_im_sessions(self.db)

        self.assertEqual(processed_count, 0)
        mock_ai.assert_not_called()


if __name__ == "__main__":
    unittest.main()