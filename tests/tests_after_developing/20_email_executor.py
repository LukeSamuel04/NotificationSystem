# tests/tests_after_developing/20_test_email_executor.py
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.ai.managers.email_executor import process_pending_emails
from app.models.notifications import Notification
from app.models.account import FetchAccount
from app.models.email_analysis import EmailAnalysis


class TestEmailExecutor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """构造通用 Mock 数据库与基础数据载荷"""
        self.mock_db = MagicMock()

        # 虚拟一个待处理的邮件 Thread 载荷 (subject, account_id)
        self.mock_pending_tuple = [("Urgent: Server Down", 202)]

        # 虚拟查询到的一条最新未读邮件
        self.mock_latest_msg = MagicMock(spec=Notification)
        self.mock_latest_msg.id = 888
        self.mock_latest_msg.external_sender_id = "boss@company.com"
        self.mock_latest_msg.received_at = datetime.now()

        # 虚拟一个健康的绑定的邮箱账号
        self.mock_valid_account = MagicMock(spec=FetchAccount)

    @patch("workers.ai.managers.email_executor.PriorityOrchestrator")
    @patch("workers.ai.managers.email_executor.analyze_email_context", new_callable=AsyncMock)
    @patch("workers.ai.managers.email_executor.get_email_formatted_context", new_callable=AsyncMock)
    async def test_executor_full_pipeline_with_fusion_orchestrator(self, mock_get_context, mock_ai_scorer,
                                                                   mock_orchestrator_cls):
        """【核心测试 1】Email AI与综合算法握手：证明 Executor 完美调用了 Orchestrator 并回写 EmailAnalysis 表"""

        # 1. 精准拦截并路由 DB 的各类查询
        def db_query_side_effect(*args, **kwargs):
            mock_q = MagicMock()

            # 路由 A：查询 pending_threads (传入的是 Notification.subject 等列属性)
            if len(args) > 0 and args[0] is Notification.subject:
                mock_q.filter.return_value.distinct.return_value.all.return_value = self.mock_pending_tuple
            # 路由 B：账号有效性校验
            elif args[0] is FetchAccount:
                mock_q.filter.return_value.first.return_value = self.mock_valid_account
            # 路由 C：获取最新邮件 或 更新状态
            elif args[0] is Notification:
                mock_q.filter.return_value.order_by.return_value.first.return_value = self.mock_latest_msg
            # 路由 D：查询是否已存在 EmailAnalysis 分析记录
            elif args[0] is EmailAnalysis:
                mock_q.filter_by.return_value.first.return_value = None  # 返回 None 触发新建

            return mock_q

        self.mock_db.query.side_effect = db_query_side_effect

        # 2. 模拟 Context 获取到的历史剧本
        mock_get_context.return_value = "Mocked Email Context Script"

        # 3. 模拟大模型 (LLM) 解析回来的高维数据特征
        mock_ai_result = MagicMock()
        mock_ai_result.priority_score = 9
        mock_ai_result.summary = "Server is down, needs immediate reboot"
        mock_ai_result.category_id = "alert_p0"
        mock_ai_scorer.return_value = mock_ai_result

        # 4. 🚀 核心：拦截综合评分引擎 (PriorityOrchestrator) 并设定期望返回值
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator_cls.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.resolve_priority.return_value = {"final_priority": 98.0}

        # --- 执行动作 ---
        processed_count = await process_pending_emails(self.mock_db)

        # --- 强力断言 ---
        # 验证成功处理了 1 个 Thread
        self.assertEqual(processed_count, 1)

        # 验证是否成功实例化并插入了 EmailAnalysis 特征分析表
        self.mock_db.add.assert_called_once()
        inserted_analysis = self.mock_db.add.call_args[0][0]
        self.assertIsInstance(inserted_analysis, EmailAnalysis)
        self.assertEqual(inserted_analysis.notification_id, 888)
        self.assertEqual(inserted_analysis.priority_score, 98.0)  # 必须存入的是综合融合后的 98分，而不是原始的 9分！

        # 🚀 证明 AI 与融合引擎成功握手！
        mock_orchestrator_instance.resolve_priority.assert_called_once_with(
            account_id="202",
            notification_id=888,
            external_sender_id="boss@company.com",
            ai_score=9,  # LLM 算出的 9 分完美交接给了 Orchestrator
            current_topic="Server is down, needs immediate reboot"[:50],  # 验证 Topic 截断传参
            platform="email"
        )

        # 验证最终数据提交
        self.mock_db.commit.assert_called_once()

    @patch("workers.ai.managers.email_executor.PriorityOrchestrator")
    async def test_executor_empty_queue_fast_exit(self, mock_orchestrator_cls):
        """【边界测试 2】空转防御验证：当邮箱没有任何新邮件时，光速退出，绝不浪费算力"""

        # 拦截传入的字段查询，强行返回空列表
        def empty_query(*args):
            mock_q = MagicMock()
            mock_q.filter.return_value.distinct.return_value.all.return_value = []
            return mock_q

        self.mock_db.query.side_effect = empty_query

        processed_count = await process_pending_emails(self.mock_db)

        self.assertEqual(processed_count, 0)
        mock_orchestrator_cls.assert_not_called()

    async def test_executor_db_commit_rollback_protection(self):
        """【灾备测试 3】事务回滚防线验证：完美避开提前 return 的陷阱，验证致命异常时的原子回滚"""

        # 💥 吸取教训：必须给一条假的待办 Thread，绕过开头的 if not pending_threads
        def dummy_thread_query(*args):
            mock_q = MagicMock()
            if len(args) > 0 and args[0] is Notification.subject:
                mock_q.filter.return_value.distinct.return_value.all.return_value = [("Dummy Subject", 999)]
            return mock_q

        self.mock_db.query.side_effect = dummy_thread_query

        # 故意制造 commit 阶段大爆炸 (模拟死锁)
        self.mock_db.commit.side_effect = Exception("Navicat Deadlock or Connection Lost")

        # 执行动作
        processed_count = await process_pending_emails(self.mock_db)

        # 容错断言：不仅返回 0，而且必须触发 rollback
        self.assertEqual(processed_count, 0)
        self.mock_db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()