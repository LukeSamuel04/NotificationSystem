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

    def _create_chainable_mock(self):
        """💥 核心基建：创建一个无限自我循环的查询 Mock，防止链式调用断层"""
        m = MagicMock()
        m.filter.return_value = m
        m.order_by.return_value = m
        m.limit.return_value = m
        return m

    async def test_get_im_context_full_two_layer_propagation(self):
        """【性能与压力测试 1】双层纵深扩散流：验证全闭环逻辑及 N+1 查询防御"""
        mock_db = MagicMock(spec=Session)

        # 1. 虚拟数据准备
        mock_prev_id = MagicMock(id=499)
        mock_next_id = MagicMock(id=501)
        mock_initial_msg = MagicMock(reply_to_mid="mid_anchor_abc")
        mock_anchor_notification = MagicMock(spec=Notification, id=300, received_at=datetime(2026, 5, 15, 18, 0, 0))

        final_records = []
        for msg_id in [300, 499, 500, 501]:
            m = MagicMock(spec=Notification, id=msg_id)
            m.received_at = datetime(2026, 5, 15, 18, 0) if msg_id == 300 else datetime(2026, 5, 15, 19, 0)
            final_records.append(m)

        # 2. 路由 Mock 构建 (使用无限循环 Mock 避免断层)
        id_query_mock = self._create_chainable_mock()
        id_query_mock.all.side_effect = [[mock_prev_id], [mock_next_id], [], [], [], []]

        mid_query_mock = self._create_chainable_mock()
        mid_query_mock.all.return_value = [mock_initial_msg]

        notification_query_mock = self._create_chainable_mock()
        notification_query_mock.all.side_effect = [[mock_anchor_notification], final_records]

        def query_routing_side_effect(*args, **kwargs):
            entity_str = str(args[0])
            if args[0] is Notification.id or entity_str.endswith(".id"):
                return id_query_mock
            elif args[0] is Notification.reply_to_mid or entity_str.endswith(".reply_to_mid"):
                return mid_query_mock
            elif args[0] is Notification:
                return notification_query_mock
            return self._create_chainable_mock()

        mock_db.query.side_effect = query_routing_side_effect

        # 3. 执行动作
        context_list = await get_im_context(mock_db, self.current_msg, window_size=10)

        # 4. 业务断言
        self.assertIsNotNone(context_list)
        self.assertEqual(len(context_list), 4)
        returned_ids = [m.id for m in context_list]
        self.assertIn(300, returned_ids)

        # 5. 性能级断言：理论上只需查 7 次
        self.assertEqual(mock_db.query.call_count, 7,
                         "性能警告：发生 N+1 查询泄露！双层单锚点扩散只允许进行精准的 7 次 SQL 查询。")

    async def test_get_im_context_isolated_no_history(self):
        """【极端边界测试 2】无历史记录：确保单兵作战稳定"""
        mock_db = MagicMock(spec=Session)

        mock_query = self._create_chainable_mock()
        mock_query.all.return_value = []

        mock_final_query = self._create_chainable_mock()
        # 💥 核心修复：第一次查锚点返回空，第二次全量汇总返回自己
        mock_final_query.all.side_effect = [[], [self.current_msg]]

        def strict_routing(*args, **kwargs):
            return mock_final_query if args[0] is Notification else mock_query

        mock_db.query.side_effect = strict_routing

        result = await get_im_context(mock_db, self.current_msg)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, 500)
        # 性能断言：1.查前 2.查后 3.查mid 4.查锚点本体(返回空,不进循环) 5.全量
        self.assertEqual(mock_db.query.call_count, 5)

    async def test_get_im_context_pure_timeline_no_references(self):
        """【算法优化测试 3】纯时间线短路：无任何引用时，证明系统完美跳过第二层嵌套查询"""
        mock_db = MagicMock(spec=Session)

        # 制造一个没有任何引用的普通消息
        plain_msg = MagicMock(spec=Notification, id=100, platform="instagram", reply_to_mid=None)

        mock_query = self._create_chainable_mock()
        mock_query.all.return_value = []

        mock_final_query = self._create_chainable_mock()
        mock_final_query.all.return_value = [plain_msg]

        def strict_routing(*args, **kwargs):
            return mock_final_query if args[0] is Notification else mock_query

        mock_db.query.side_effect = strict_routing

        result = await get_im_context(mock_db, plain_msg)

        self.assertEqual(len(result), 1)
        # 性能断言：无引用，跳过锚点逻辑，只需查 4 次
        self.assertEqual(mock_db.query.call_count, 4, "算法优化失败：系统在没有引用的情况下浪费了数据库算力。")

    async def test_get_im_context_dangling_reference(self):
        """【灾难防御测试 4】幽灵锚点/断链防御：当引用的原消息被物理删除，系统必须平滑降级，绝不崩溃"""
        mock_db = MagicMock(spec=Session)

        id_query_mock = self._create_chainable_mock()
        id_query_mock.all.return_value = []

        mid_query_mock = self._create_chainable_mock()
        mid_query_mock.all.return_value = []

        notification_query_mock = self._create_chainable_mock()
        # 第一波查 anchors 时返回空（原消息丢了），第二波查汇总返回自己
        notification_query_mock.all.side_effect = [[], [self.current_msg]]

        def query_routing_side_effect(*args, **kwargs):
            entity_str = str(args[0])
            if args[0] is Notification.id or entity_str.endswith(".id"):
                return id_query_mock
            elif args[0] is Notification.reply_to_mid or entity_str.endswith(".reply_to_mid"):
                return mid_query_mock
            elif args[0] is Notification:
                return notification_query_mock

        mock_db.query.side_effect = query_routing_side_effect

        result = await get_im_context(mock_db, self.current_msg)

        # 业务断言：断链时平滑降级
        self.assertEqual(len(result), 1)
        # 性能断言：查锚点发现断链 -> 直接跳过锚点扩散 -> 全量汇总，共查 5 次
        self.assertEqual(mock_db.query.call_count, 5, "灾备逻辑异常：在断链时执行了多余的死循环查询。")


if __name__ == "__main__":
    unittest.main()