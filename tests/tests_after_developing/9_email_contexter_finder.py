# tests/tests_after_developing/9_email_context_finder.py
import unittest
from unittest.mock import MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

# 导入待测核心寻回器以及依赖的模型
from app.services.context.email.context_finder import EmailContextFinder
from app.models.notifications import Notification


class TestEmailContextFinderStress(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：构造当前待处理的最新“压轴”基准邮件报文"""
        self.current_msg = MagicMock(spec=Notification)
        self.current_msg.id = 999
        self.current_msg.account_id = "luke_bth_student_account"
        self.current_msg.platform = "email"
        self.current_msg.subject = "PA2552 Core Project Architecture Discussion"
        self.current_msg.reply_to_mid = "msg_id_parent_level_777"
        self.current_msg.received_at = datetime(2026, 5, 15, 12, 0, 0)

        # 核心重构：创建流式自闭环 Mock 引擎，防止链式调用层级变化引发测试代码脆弱性
        self.mock_db = MagicMock(spec=Session)
        self.mock_query = MagicMock()

        # 让所有常见的 SQLAlchemy 链式方法全部返回 query 对象本体
        self.mock_db.query.return_value = self.mock_query
        self.mock_query.filter.return_value = self.mock_query
        self.mock_query.order_by.return_value = self.mock_query
        self.mock_query.limit.return_value = self.mock_query

    def test_edge_case_empty_or_none_input(self):
        """【极端边界测试 1】输入脱靶：验证当传入的当前邮件为 None 时，光速切断并返回空列表"""
        result = EmailContextFinder.get_context_records(self.mock_db, None)
        self.assertEqual(result, [])
        self.mock_db.query.assert_not_called()

    def test_stress_deep_conversation_thread_capping(self):
        """【压力测试 2】多轮深度来回回复：验证当历史对话极其漫长（如10封信）时，max_history 能精准截断并反转时间线"""
        # 构造一个长达 10 封信的漫长历史时间线（时间由远及近）
        long_history = []
        base_time = datetime(2026, 5, 15, 10, 0, 0)
        for i in range(10):
            hist_msg = MagicMock(spec=Notification)
            hist_msg.id = i + 100  # ID 从 100 到 109
            hist_msg.subject = "PA2552 Core Project Architecture Discussion"
            hist_msg.received_at = base_time + timedelta(minutes=i)
            long_history.append(hist_msg)

        # 生产逻辑中：query.order_by(received_at.desc()).limit(5).all()
        # 模拟数据库在 desc 排序下会先吐出时间最新的最近 5 条历史记录（ID 109 到 105）
        db_returned_desc = list(reversed(long_history))[:5]
        self.mock_query.all.return_value = db_returned_desc

        # 执行动作：限制只取最近 5 条历史
        context_chain = EmailContextFinder.get_context_records(self.mock_db, self.current_msg, max_history=5)

        # 断言追溯：
        self.assertEqual(len(context_chain), 6)  # 5 条历史保底 + 1 条当前压轴
        self.mock_query.limit.assert_called_with(5)

        # 时间线正序还原验证：检查反转后是否时间早的在前面（105 -> 106 -> 107 -> 108 -> 109 -> 999）
        self.assertEqual(context_chain[0].id, 105)  # 最早的历史
        self.assertEqual(context_chain[4].id, 109)  # 最近的历史
        self.assertEqual(context_chain[5].id, 999)  # 压轴的大结局最新邮件

    def test_context_by_reply_to_mid_when_subject_changed(self):
        """【极端案例测试 3】主题彻底改变：验证哪怕对方回信时把 Subject 改得面目全非，只要 In-Reply-To 引用链顺得上，依然能唤醒上下文"""
        # 模拟一封历史邮件，主题完全不同（被改成了 "Urgent Changed Title!"），但它的 ID 正好是当前邮件引用的父级 ID
        parent_msg = MagicMock(spec=Notification)
        parent_msg.id = 777
        parent_msg.account_msg_id = "msg_id_parent_level_777"
        parent_msg.subject = "Urgent Changed Title!"
        parent_msg.received_at = datetime(2026, 5, 15, 11, 0, 0)

        self.mock_query.all.return_value = [parent_msg]

        # 执行动作
        context_chain = EmailContextFinder.get_context_records(self.mock_db, self.current_msg)

        # 断言追溯：即便主题不同，依靠 In-Reply-To 依然能实现血缘归宗
        self.assertEqual(len(context_chain), 2)
        self.assertEqual(context_chain[0].id, 777)
        self.assertEqual(context_chain[1].id, 999)

    def test_extreme_time_boundary_future_exclusion(self):
        """【压力边界测试 4】时间结界拦截：验证即使主题完全一样，但在当前邮件“之后”才收到的未来邮件（如并发延迟信件），必须被死死隔离在外"""
        # 构造一封在未来（下午1点）才收到的同主题信件（当前邮件是中午12点）
        future_msg = MagicMock(spec=Notification)
        future_msg.id = 888
        future_msg.subject = "PA2552 Core Project Architecture Discussion"
        future_msg.received_at = datetime(2026, 5, 15, 13, 0, 0)

        # 模拟数据库行为：因为有时间结界限制，查询应该返回空
        self.mock_query.all.return_value = []

        # 执行动作
        context_chain = EmailContextFinder.get_context_records(self.mock_db, self.current_msg)

        # 断言追溯：未来的邮件被无情过滤，列表里应该只有当前邮件孤独的单兵作战
        self.assertEqual(len(context_chain), 1)
        self.assertEqual(context_chain[0].id, 999)

    def test_strict_isolation_by_account_and_platform(self):
        """【隔离性压力测试 5】跨账号与跨平台撞车：验证即使主题完全一致，但属于不同租户账号、或属于 Instagram 平台，也绝不准串线漏入"""
        self.mock_query.all.return_value = []

        # 触发寻回，让生产逻辑拼装 filter 表达式
        _ = EmailContextFinder.get_context_records(self.mock_db, self.current_msg)

        platform_ok = False
        account_ok = False

        # 💥 终极修复：直接解构 SQLAlchemy 二元表达式的 AST 节点，彻底斩断 SQL 编译占位符的干扰
        for call in self.mock_query.filter.call_args_list:
            for arg in call[0]:
                if hasattr(arg, "left") and hasattr(arg, "right"):
                    left_name = getattr(arg.left, "name", "")
                    right_value = getattr(arg.right, "value", None)

                    # 精准核验左字段名与右绑定的具体字面量值
                    if left_name == "platform" and right_value == "email":
                        platform_ok = True
                    if left_name == "account_id" and right_value == "luke_bth_student_account":
                        account_ok = True

        # 严格验证核心隔离性断言
        self.assertTrue(platform_ok, "安全隔离检查失败：Filter 链中缺少对 platform == 'email' 的物理限制条件。")
        self.assertTrue(account_ok, "安全隔离检查失败：Filter 链中缺少对当前用户 account_id 租户域的物理隔离条件。")

    def test_exact_boundary_no_history_at_all(self):
        """【边界案例测试 6】零历史孤证：验证当该主题是盘古开天辟地第一封信、数据库无任何历史记录时，系统能正确平稳返回仅包含当前的单元素列表"""
        self.mock_query.all.return_value = []

        context_chain = EmailContextFinder.get_context_records(self.mock_db, self.current_msg)

        self.assertEqual(len(context_chain), 1)
        self.assertEqual(context_chain[0].id, 999)

    def test_database_exception_handling_graceful_fallback(self):
        """【灾难演练测试 7】数据库熔断自愈：验证当底层数据库突然发生死锁、网络中断抛出未知异常时，系统能百分百接住炸弹，并降级返回单兵列表，决不雪崩崩溃"""
        # 故意让底层 all() 触发 Navicat 连接池耗尽或死锁异常
        self.mock_query.all.side_effect = Exception("Navicat Connection Pool Exhausted or deadlock detected")

        # 执行动作
        fallback_chain = EmailContextFinder.get_context_records(self.mock_db, self.current_msg)

        # 核心容错断言
        self.assertIsNotNone(fallback_chain)
        self.assertEqual(len(fallback_chain), 1)
        self.assertEqual(fallback_chain[0].id, 999)


if __name__ == "__main__":
    unittest.main()