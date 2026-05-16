# tests/tests_after_developing/16_im_scheduler.py
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.ai.managers.im_scheduler import (
    start_im_scheduler,
    perform_scan,
    trigger_immediate_scan
)
import workers.ai.managers.im_scheduler as im_module

# 🚀 核心修复 1：保存真实的 asyncio.sleep，防止被 @patch 污染全局事件循环导致不让出控制权
real_sleep = asyncio.sleep


class TestIMScheduler(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # 每次测试都会创建新事件循环，必须让全局 Event 重新绑定到当前的新循环上！
        im_module._scan_trigger = asyncio.Event()

    @patch("workers.ai.managers.im_scheduler.SessionLocal")
    @patch("workers.ai.managers.im_scheduler.process_pending_im_sessions", new_callable=AsyncMock)
    async def test_perform_scan_success_and_db_release(self, mock_process, mock_session_local):
        """【测试 1】单次扫盘与内存防漏：验证 Executor 成功执行后，数据库连接必定被关闭"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_process.return_value = 5

        await perform_scan()

        mock_process.assert_called_once_with(mock_db)
        mock_db.close.assert_called_once()

    @patch("workers.ai.managers.im_scheduler.SessionLocal")
    @patch("workers.ai.managers.im_scheduler.process_pending_im_sessions", new_callable=AsyncMock)
    async def test_perform_scan_exception_db_release(self, mock_process, mock_session_local):
        """【测试 2】极端单次扫盘崩溃：验证即使底层抛错，finally 依然能兜底释放数据库连接"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_process.side_effect = Exception("Gemini API Rate Limit Exceeded")

        await perform_scan()

        mock_db.close.assert_called_once()

    @patch("workers.ai.managers.im_scheduler.perform_scan", new_callable=AsyncMock)
    async def test_scheduler_loop_trigger_immediate_scan(self, mock_perform_scan):
        """【测试 3】死循环 Webhook 唤醒：模拟新入库请求，验证 _scan_trigger 能瞬间打断休眠并执行扫盘"""
        task = asyncio.create_task(start_im_scheduler())

        # 使用未被污染的 real_sleep 让出控制权
        await real_sleep(0.05)
        self.assertEqual(mock_perform_scan.call_count, 1)

        trigger_immediate_scan()

        await real_sleep(0.05)
        self.assertEqual(mock_perform_scan.call_count, 2)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @patch("workers.ai.managers.im_scheduler.asyncio.wait_for")
    @patch("workers.ai.managers.im_scheduler.perform_scan", new_callable=AsyncMock)
    async def test_scheduler_loop_timeout_fallback(self, mock_perform_scan, mock_wait_for):
        """【测试 4】30 秒干旱兜底：验证如果 30 秒内 Webhook 静默，死循环能平滑捕获 TimeoutError 并自主扫盘"""

        # 🚀 核心修复 2：拦截传入的 coro 并 close()，彻底消除 "never awaited" 的警告
        async def mock_timeout_behavior(coro, *args, **kwargs):
            coro.close()
            await real_sleep(0.001)
            raise asyncio.TimeoutError()

        mock_wait_for.side_effect = mock_timeout_behavior

        task = asyncio.create_task(start_im_scheduler())
        await real_sleep(0.05)

        self.assertTrue(mock_perform_scan.call_count >= 2)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @patch("workers.ai.managers.im_scheduler.asyncio.sleep", new_callable=AsyncMock)
    @patch("workers.ai.managers.im_scheduler.asyncio.wait_for")
    @patch("workers.ai.managers.im_scheduler.perform_scan", new_callable=AsyncMock)
    async def test_scheduler_loop_severe_exception_resilience(self, mock_perform_scan, mock_wait_for, mock_sleep):
        """【极端案例测试 5】进程雪崩防死锁：验证产生未预料错误时，系统能强制休眠降温并自我恢复"""

        async def mock_severe_error(coro, *args, **kwargs):
            coro.close()  # 同样关闭遗留协程防止红字警告
            await real_sleep(0.001)
            raise Exception("Simulated Event Loop Catastrophic Failure")

        mock_wait_for.side_effect = mock_severe_error

        task = asyncio.create_task(start_im_scheduler())
        await real_sleep(0.05)

        # 现在的 mock_sleep 只会捕获到生产代码里调用的 sleep(5)
        mock_sleep.assert_called_with(5)
        self.assertTrue(mock_perform_scan.call_count >= 2)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    unittest.main()