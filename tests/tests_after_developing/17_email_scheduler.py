# tests/tests_after_developing/17_test_email_scheduler.py
import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.ai.managers.email_scheduler import (
    start_email_scheduler,
    perform_email_scan,
    trigger_email_scan
)
# 引入模块本身，用于动态修正绑定在老事件循环上的全局变量
import workers.ai.managers.email_scheduler as email_module

# 🚀 核心防线：保存真实的 asyncio.sleep，防止被 @patch 污染全局事件循环
real_sleep = asyncio.sleep


class TestEmailScheduler(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """每次测试前清理全局状态，绑定新事件循环"""
        # 强制将全局事件绑定到当前测试类生成的新 asyncio Loop 上，防止“Task attached to a different loop”报错
        email_module._email_scan_trigger = asyncio.Event()

    @patch("workers.ai.managers.email_scheduler.SessionLocal")
    @patch("workers.ai.managers.email_scheduler.process_pending_emails", new_callable=AsyncMock)
    async def test_perform_scan_success_and_db_release(self, mock_process, mock_session_local):
        """【测试 1】单次扫盘与内存防漏：验证 Executor 成功执行后，数据库连接必定被关闭"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        mock_process.return_value = 10  # 模拟成功处理了 10 个邮件 Thread

        await perform_email_scan()

        # 断言：完美传导 Session 并最终调用 close() 释放池连接
        mock_process.assert_called_once_with(mock_db)
        mock_db.close.assert_called_once()

    @patch("workers.ai.managers.email_scheduler.SessionLocal")
    @patch("workers.ai.managers.email_scheduler.process_pending_emails", new_callable=AsyncMock)
    async def test_perform_scan_exception_db_release(self, mock_process, mock_session_local):
        """【测试 2】极端单次扫盘崩溃：验证即使底层抛错，finally 依然能死死兜底释放数据库连接"""
        mock_db = MagicMock()
        mock_session_local.return_value = mock_db
        # 故意制造一个极其致命的异常抛出
        mock_process.side_effect = Exception("Email LLM Parsing Error or Connection Timeout")

        await perform_email_scan()

        # 断言：顶层接住炸弹不崩溃，并且铁面无私地执行了 db.close()
        mock_db.close.assert_called_once()

    @patch("workers.ai.managers.email_scheduler.perform_email_scan", new_callable=AsyncMock)
    async def test_scheduler_loop_trigger_immediate_scan(self, mock_perform_scan):
        """【测试 3】死循环唤醒测试：模拟新邮件入库请求，验证 trigger_email_scan 能瞬间打断休眠并执行扫盘"""
        # 把死循环挂载到后台并发任务中
        task = asyncio.create_task(start_email_scheduler())

        # 让出控制权，让启动时的第 1 次无条件扫盘跑完
        await real_sleep(0.05)
        self.assertEqual(mock_perform_scan.call_count, 1)

        # 模拟拉取引擎 (fetch_manager) 按响了新邮件的门铃！
        trigger_email_scan()

        # 让出控制权，验证死循环瞬间醒来执行第 2 次扫盘
        await real_sleep(0.05)
        self.assertEqual(mock_perform_scan.call_count, 2)

        # 体面击杀后台死循环任务
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @patch("workers.ai.managers.email_scheduler.asyncio.wait_for")
    @patch("workers.ai.managers.email_scheduler.perform_email_scan", new_callable=AsyncMock)
    async def test_scheduler_loop_timeout_fallback(self, mock_perform_scan, mock_wait_for):
        """【测试 4】30 秒干旱兜底：验证如果 30 秒内没有任何新邮件，死循环能平滑捕获 TimeoutError 并自主扫盘"""

        # 🚀 内存防漏护城河：拦截传入的 coro 并 close()，彻底消除 "never awaited" 警告
        async def mock_timeout_behavior(coro, *args, **kwargs):
            coro.close()
            await real_sleep(0.001)  # 打破死锁
            raise asyncio.TimeoutError()

        mock_wait_for.side_effect = mock_timeout_behavior

        task = asyncio.create_task(start_email_scheduler())
        await real_sleep(0.05)

        # 断言：除了启动的 1 次，兜底逻辑至少又触发了 1 次
        self.assertTrue(mock_perform_scan.call_count >= 2)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    @patch("workers.ai.managers.email_scheduler.asyncio.sleep", new_callable=AsyncMock)
    @patch("workers.ai.managers.email_scheduler.asyncio.wait_for")
    @patch("workers.ai.managers.email_scheduler.perform_email_scan", new_callable=AsyncMock)
    async def test_scheduler_loop_severe_exception_resilience(self, mock_perform_scan, mock_wait_for, mock_sleep):
        """【极端案例测试 5】进程雪崩防死锁：验证当死循环内部产生未预料错误时，系统能强制休眠 5 秒降温，绝不雪崩"""

        async def mock_severe_error(coro, *args, **kwargs):
            coro.close()  # 回收协程垃圾
            await real_sleep(0.001)
            raise Exception("Simulated Email Event Loop Catastrophic Failure")

        mock_wait_for.side_effect = mock_severe_error

        task = asyncio.create_task(start_email_scheduler())
        await real_sleep(0.05)

        # 核心防线断言：验证是否触发了防御性休眠 (sleep(5))
        mock_sleep.assert_called_with(5)
        # 即使发生了大爆炸，休眠结束后，代码依然坚强地继续调用了扫盘
        self.assertTrue(mock_perform_scan.call_count >= 2)

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


if __name__ == "__main__":
    unittest.main()