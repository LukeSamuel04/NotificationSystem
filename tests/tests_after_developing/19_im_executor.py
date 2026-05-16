# tests/tests_after_developing/19_test_im_executor.py
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.ai.managers.im_executor import process_pending_im_sessions
from app.models.notifications import Notification
from app.models.account import FetchAccount
from app.models.im_session import IMSessionState


class TestIMExecutor(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """构造通用 Mock 数据库与基础数据载荷"""
        self.mock_db = MagicMock()

        # 虚拟一个待处理的会话载荷 (sender_id, account_id, platform)
        self.mock_pending_tuple = [("gymbro_666", 101, "instagram")]

        # 虚拟查询到的一条最新未读消息
        self.mock_latest_msg = MagicMock(spec=Notification)
        self.mock_latest_msg.id = 999
        self.mock_latest_msg.received_at = datetime.now()

        # 虚拟一个健康的绑定的商业账号
        self.mock_valid_account = MagicMock(spec=FetchAccount)

    @patch("workers.ai.managers.im_executor.PriorityOrchestrator")
    @patch("workers.ai.managers.im_executor.analyze_social_media_session", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_executor.get_formatted_context", new_callable=AsyncMock)
    async def test_executor_full_pipeline_with_fusion_orchestrator(self, mock_get_context, mock_ai_scorer,
                                                                   mock_orchestrator_cls):
        """【核心测试 1】AI与综合算法握手验证：证明 Executor 完美调用了 Orchestrator 进行泊松偏好融合计算"""

        # 1. 拦截并设置 DB 各种查询的返回路径
        def db_query_side_effect(model, *args):
            mock_q = MagicMock()
            if hasattr(model, "class_") and model.class_ == Notification:
                # 对应第一步：获取 pending_sessions 元组
                mock_q.filter.return_value.distinct.return_value.all.return_value = self.mock_pending_tuple
            elif model == FetchAccount:
                # 对应账号校验
                mock_q.filter.return_value.first.return_value = self.mock_valid_account
            elif model == Notification:
                # 对应获取 latest_msg
                mock_q.filter.return_value.order_by.return_value.first.return_value = self.mock_latest_msg
            elif model == IMSessionState:
                # 对应前置显式建档检查：返回 None 触发新建
                mock_q.filter_by.return_value.first.return_value = None
            return mock_q

        self.mock_db.query.side_effect = db_query_side_effect

        # 2. 模拟 Context 获取到的历史剧本
        mock_get_context.return_value = "Mocked Context Script"

        # 3. 模拟大模型 (LLM) 解析回来的结果字典/对象
        mock_ai_result = MagicMock()
        mock_ai_result.priority_score = 8
        mock_ai_result.current_topic = "Fitness Plan"
        mock_ai_result.summary_snapshot = "Discussing leg day"
        mock_ai_scorer.return_value = mock_ai_result

        # 4. 🚀 核心：拦截综合评分引擎 (PriorityOrchestrator) 并设定期望返回值
        mock_orchestrator_instance = MagicMock()
        mock_orchestrator_cls.return_value = mock_orchestrator_instance
        mock_orchestrator_instance.resolve_priority.return_value = {"final_priority": 95.5}

        # --- 执行动作 ---
        processed_count = await process_pending_im_sessions(self.mock_db)

        # --- 强力断言 ---
        # 验证是否成功处理了 1 个会话
        self.assertEqual(processed_count, 1)

        # 验证是否触发了显式冷表建档 (db.add 被调用插入了新 IMSessionState)
        self.mock_db.add.assert_called_once()
        inserted_state = self.mock_db.add.call_args[0][0]
        self.assertIsInstance(inserted_state, IMSessionState)
        self.assertEqual(inserted_state.external_sender_id, "gymbro_666")

        # 🚀 证明 AI 与融合引擎成功握手：验证 Orchestrator 是否被正确传入了参数！
        mock_orchestrator_instance.resolve_priority.assert_called_once_with(
            account_id="101",
            notification_id=999,
            external_sender_id="gymbro_666",
            ai_score=8,  # 确保 LLM 算出的 8 分传给了融合器
            current_topic="Fitness Plan",
            platform="instagram"
        )

        # 验证最终数据提交
        self.mock_db.commit.assert_called_once()

    @patch("workers.ai.managers.im_executor.PriorityOrchestrator")
    async def test_executor_empty_queue_fast_exit(self, mock_orchestrator_cls):
        """【边界测试 2】空转防御验证：当没有任何待处理消息时，光速退出，绝不浪费 CPU 与 DB 连接"""
        # 第一层查询直接返回空列表
        self.mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []

        processed_count = await process_pending_im_sessions(self.mock_db)

        self.assertEqual(processed_count, 0)
        # 确认没有实例化融合引擎，彻底阻断了后续一切开销
        mock_orchestrator_cls.assert_not_called()

    async def test_executor_db_commit_rollback_protection(self):
        """【灾备测试 3】事务回滚防线验证：验证在提交阶段遇到死锁等致命异常时，能触发原子回滚"""

        # 💥 核心修复：必须给一条假的待办任务，绕过开头的 if not pending_sessions 拦截，让代码能往下走
        self.mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [
            ("dummy_user", 101, "instagram")]

        # 故意制造 commit 阶段大爆炸
        self.mock_db.commit.side_effect = Exception("Navicat Deadlock or Connection Lost")

        # 执行动作
        processed_count = await process_pending_im_sessions(self.mock_db)

        # 容错断言
        self.assertEqual(processed_count, 0)
        self.mock_db.rollback.assert_called_once()


if __name__ == "__main__":
    unittest.main()