# test/test_email_scheduler_with_orchestrator.py
import unittest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base_class import Base
from app.models.notifications import Notification
from app.models.email_analysis import EmailAnalysis
from app.models.user_preference import UserPreference
from app.models.analysis_payload import AnalysisPayload
from app.models.account import FetchAccount
from workers.ai.managers.email_executor import process_pending_emails


class TestEmailSchedulerIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self.db = self.SessionLocal()

        # 💥 核心同步归一化：严格使用纯字符串类型
        self.acc_id = "1001"

        self.db.add(UserPreference(
            account_id=self.acc_id, platform="email",
            preference_type="email_domain", target_value="bth.se", preference_factor=1.5
        ))

        valid_account = FetchAccount(
            id=self.acc_id,
            platform_account_id="bth_imap_user_hash_1024",
            platform="email",
            username="student_user_bth",
            config="{}",
            is_valid=1,
            is_active=1
        )
        self.db.add(valid_account)
        self.db.commit()

    async def asyncTearDown(self):
        self.db.close()

    @patch("workers.ai.managers.email_executor.analyze_email_context", new_callable=AsyncMock)
    @patch("workers.ai.managers.email_executor.get_email_formatted_context", new_callable=AsyncMock)
    async def test_1_email_domain_extraction_precision(self, mock_context, mock_ai):
        msg = Notification(
            account_id=self.acc_id, platform="email",
            account_msg_id="email_hash_001", external_sender_id="advisor@bth.se",
            subject="Master Thesis Submission Deadline", status="pending"
        )
        self.db.add(msg)
        self.db.commit()

        mock_ai.return_value = type('obj', (object,), {
            'priority_score': 6, 'category_id': 1, 'summary': 'Thesis review info.'
        })
        mock_context.return_value = "Formatted email headers and contents."

        await process_pending_emails(self.db)

        analysis = self.db.query(EmailAnalysis).filter_by(notification_id=msg.id).first()
        self.assertIsNotNone(analysis)
        self.assertEqual(analysis.priority_score, 7)

        payload = self.db.query(AnalysisPayload).filter_by(notification_id=msg.id).first()
        self.assertEqual(payload.analysis_data["metadata"]["domain"], "bth.se")

    @patch("workers.ai.managers.email_executor.analyze_email_context", new_callable=AsyncMock)
    @patch("workers.ai.managers.email_executor.get_email_formatted_context", new_callable=AsyncMock)
    async def test_2_email_high_concurrency_deduplication(self, mock_context, mock_ai):
        target_subject = "[GitHub] Issue assigned to you"
        for i in range(8):
            self.db.add(Notification(
                account_id=self.acc_id, platform="email",
                account_msg_id=f"github_bomb_{i}", external_sender_id="notifications@github.com",
                subject=target_subject, status="pending"
            ))
        self.db.commit()

        mock_ai.return_value = type('obj', (object,), {
            'priority_score': 5, 'category_id': 3, 'summary': 'Batch build updates.'
        })
        mock_context.return_value = "Aggregated long thread text."

        processed_threads = await process_pending_emails(self.db)

        self.assertEqual(processed_threads, 1)
        mock_ai.assert_called_once()

        pending_remains = self.db.query(Notification).filter_by(status="pending").count()
        self.assertEqual(pending_remains, 0)

        payload_count = self.db.query(AnalysisPayload).count()
        self.assertEqual(payload_count, 1)


if __name__ == "__main__":
    unittest.main()