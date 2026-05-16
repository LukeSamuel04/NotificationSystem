# test/workers/1_availability_tester.py
import asyncio
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
from sqlalchemy.orm import Session

# 导入业务模型与目标测试函数
from app.models.account import FetchAccount
from workers.account.availability_tester import (
    check_single_account,
    tester_loop,
    FAIL_COUNTS
)


class TestAvailabilityTester(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """每单元测试开始前执行，确保内存防抖计数器保持纯净"""
        FAIL_COUNTS.clear()

    def tearDown(self):
        """测试结束后清理"""
        FAIL_COUNTS.clear()

    @patch("workers.account.availability_tester.asyncio.open_connection")
    async def test_is_internet_connected_success(self, mock_open_connection):
        """验证：当公网 DNS 可达时，网络连通性检查器返回 True"""
        from workers.account.availability_tester import is_internet_connected_async

        # Mock 异步网络流的 writer 闭合机制
        mock_writer = AsyncMock()
        mock_open_connection.return_value = (AsyncMock(), mock_writer)

        result = await is_internet_connected_async()
        self.assertTrue(result)
        mock_open_connection.assert_called_once_with("1.1.1.1", 53)

    async def test_check_single_account_success(self):
        """验证：当探针实例连接测试成功时，账号健康标识被强行置为 True，且失败计数清零"""
        # 1. 组装虚拟 ORM 账号资产
        mock_account = MagicMock(spec=FetchAccount)
        mock_account.id = 42
        mock_account.username = "luke@bth.se"
        mock_account.platform = "email"
        mock_account.is_valid = False  # 初始状态为失联

        # 2. 模拟健康的探针实例
        mock_tester_instance = AsyncMock()
        mock_tester_instance.test_connection.return_value = True

        # 3. 制造原先已经失败过一次的内存防抖印记
        FAIL_COUNTS[42] = 1
        mock_db = MagicMock(spec=Session)

        # 4. 执行单点探测
        await check_single_account(mock_account, mock_tester_instance, mock_db)

        # 5. 断言判定：健康状态应当原地自愈复活，且失败防抖计数归零
        self.assertTrue(mock_account.is_valid)
        self.assertEqual(FAIL_COUNTS[42], 0)

    async def test_check_single_account_trigger_failure_threshold(self):
        """验证：当连续验证失败达到 3 次时，防抖机制触发，将账号安全标记为失联(False)"""
        mock_account = MagicMock(spec=FetchAccount)
        mock_account.id = 99
        mock_account.username = "luke_instagram"
        mock_account.platform = "instagram"
        mock_account.is_valid = True  # 初始状态保持健康

        mock_tester_instance = AsyncMock()
        mock_tester_instance.test_connection.return_value = False

        # 模拟之前已经连续失败了 2 次的情景
        FAIL_COUNTS[99] = 2
        mock_db = MagicMock(spec=Session)

        # 执行第三次决定命运的失败探测
        await check_single_account(mock_account, mock_tester_instance, mock_db)

        # 断言判定：累加达到 3 次，防抖熔断机制介入，健康状态转为失效
        self.assertEqual(FAIL_COUNTS[99], 3)
        self.assertFalse(mock_account.is_valid)

    @patch("workers.account.availability_tester.SessionLocal")
    @patch("workers.account.availability_tester.is_internet_connected_async")
    @patch("workers.account.availability_tester.check_single_account")
    @patch("workers.account.availability_tester.EmailFetcher")
    async def test_tester_loop_execution_flow(
            self, mock_email_fetcher, mock_check_single, mock_internet_check, mock_session_local
    ):
        """
        核心鲁棒性综合断言：验证后台常驻死循环在收到 stop_event 信号时，
        能完整跑完一轮扫描（查出活跃账号、装配多态实例、发起检查、落库提交），并实现优雅优雅下线。
        """
        # 1. 拦截大网环境检查，确保顺利进入扫描
        mock_internet_check.return_value = True

        # 2. 伪造数据库底层会话行为
        mock_db_session = MagicMock(spec=Session)
        mock_session_local.return_value = mock_db_session

        # 3. 构造一条活跃的 Email 检查账号数据
        mock_account = MagicMock(spec=FetchAccount)
        mock_account.is_active = True
        mock_account.platform = "email"
        mock_account.username = "luke_test"
        mock_account.config = {"imap_server": "imap.bth.se"}

        # 让数据库查询结果返回这个虚拟账号对象
        mock_db_session.query.return_value.filter.return_value.all.return_value = [mock_account]

        # 4. 建立停机感知事件控制中心
        stop_event = asyncio.Event()

        # 💥 核心控制点：通过动态覆写 stop_event.is_set，让循环只执行一次就自动认为收到停机信号
        loop_counter = 0

        def side_effect_stop_check():
            nonlocal loop_counter
            if loop_counter >= 1:
                return True
            loop_counter += 1
            return False

        # 借助 MagicMock 接管状态检查
        mock_stop_event = MagicMock(spec=asyncio.Event)
        mock_stop_event.is_set.side_effect = side_effect_stop_check

        # 5. 挂载执行常驻 Worker 循环
        await tester_loop(mock_stop_event)

        # 6. 全链路闭环断言：
        mock_session_local.assert_called_once()  # 确保正常建立了数据库会话
        mock_email_fetcher.assert_called_once()  # 确保多态工厂为 email 账号装配了 EmailFetcher 探针
        mock_check_single.assert_called_once()  # 确保调用了探测执行逻辑
        mock_db_session.commit.assert_called_once()  # 确保健康状态的更迭成功 commit 持久化
        mock_db_session.close.assert_called_once()  # 💡 极其重要：确保 finally 机制生效，连接被回收释放，无连接池泄露风险


# 💥 核心升级：挂载标准单元测试启动飞轮，允许直接一键点击点击运行
if __name__ == "__main__":
    unittest.main()