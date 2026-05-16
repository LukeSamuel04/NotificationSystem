# tests/tests_after_developing/11_test_im_context_finder.py
import unittest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime
from sqlalchemy.orm import Session

# 导入待测异步组件与模型
from app.services.context.im.context_finder import get_im_context
from app.models.notifications import Notification


class TestIMContextFinder(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：构造当前基准待处理的最新消息"""
        self.current_msg = MagicMock(spec=Notification)
        self.current_msg.id = 500
        self.current_msg.external_sender_id = "gymbro_666"
        self.current_msg.platform = "instagram"
        self.current_msg.received_at = datetime(2026, 5, 15, 19, 0, 0)
        self.current_msg.reply_to_mid = "mid_anchor_abc"

    async def test_get_im_context_full_two_layer_propagation(self):
        """【压力测试 1】双层纵深扩散流：验证时间轴前后扩散、引用锚点捕获、二次深度扩散、去重以及正序排列的全闭环逻辑"""
        mock_db = MagicMock(spec=Session)

        # 1. 准备第一层时间轴扩散产生的虚拟 ID 数据
        mock_prev_id = MagicMock();
        mock_prev_id.id = 499
        mock_next_id = MagicMock();
        mock_next_id.id = 501

        # 2. 准备第二层逻辑引用追踪所需的父级 MID 数据
        mock_initial_msg = MagicMock()
        mock_initial_msg.reply_to_mid = "mid_anchor_abc"

        # 3. 准备二次扩散找到的物理锚点对象
        mock_anchor_notification = MagicMock(spec=Notification)
        mock_anchor_notification.id = 300
        mock_anchor_notification.received_at = datetime(2026, 5, 15, 18, 0, 0)

        # 4. 准备最终去重汇总后的完整 Notification 对象大集合
        final_records = []
        for msg_id in [300, 499, 500, 501]:
            m = MagicMock(spec=Notification)
            m.id = msg_id
            m.received_at = datetime(2026, 5, 15, 18, 0) if msg_id == 300 else datetime(2026, 5, 15, 19, 0)
            final_records.append(m)

        # 💥 核心：设计一个高度智能的路由机制，根据 query() 传入的参数类型动态响应后续的链式调用
        def query_routing_side_effect(entity):
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.order_by.return_value = mock_query
            mock_query.limit.return_value = mock_query

            # 分流判定 A：如果是提取时间线 ID 扩散 (查 Notification.id)
            if entity == Notification.id:
                # 针对 prev_ids 和 next_ids 交替返回，以及后面的 a_prev, a_next 兜底空
                mock_query.all.side_effect = [[mock_prev_id], [mock_next_id], [], []]
            # 分流判定 B：如果是提取引用链 (查 Notification.reply_to_mid)
            elif entity == Notification.reply_to_mid:
                mock_query.all.return_value = [mock_initial_msg]
            # 分流判定 C：如果是最后拉取全量Notification实体
            elif entity == Notification:
                # 第一次可能被用于查 anchors，第二次被用于查 final_context
                mock_query.all.side_effect = [[mock_anchor_notification], final_records]

            return mock_query

        mock_db.query.side_effect = query_routing_side_effect

        # 执行动作：设定扩散窗口为 10
        context_list = await get_im_context(mock_db, self.current_msg, window_size=10)

        # 5. 全业务线综合断言：
        self.assertIsNotNone(context_list)
        self.assertEqual(len(context_list), 4)  # 包含 300(锚点), 499(前), 500(当前), 501(后)

        # 验证去重后的 ID 集合是否包含了二次扩散的锚点 ID (300)
        returned_ids = [m.id for m in context_list]
        self.assertIn(300, returned_ids)
        self.assertIn(500, returned_ids)

    async def test_get_im_context_isolated_no_history(self):
        """【极端边界测试 2】开天辟地第一封信：验证当数据库空空如也、没有任何往来记录时，系统能平稳返回仅包含当前的单元素列表"""
        mock_db = MagicMock(spec=Session)

        # 让所有的 .all() 统一返回空列表
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.all.side_effect = [[], [], [], []]  # prev, next, initial_msgs 均为空

        # 最终拉取全量时，只有当前消息自己
        mock_final_query = MagicMock()
        mock_final_query.filter.return_value = mock_final_query
        mock_final_query.order_by.return_value = mock_final_query
        mock_final_query.all.return_value = [self.current_msg]

        def strict_routing(entity):
            return mock_final_query if entity == Notification else mock_query

        mock_db.query.side_effect = strict_routing

        # 执行动作
        result = await get_im_context(mock_db, self.current_msg)

        # 断言追溯：无历史包袱时，确保单兵作战，不抛异常
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 500)


if __name__ == "__main__":
    unittest.main()