# tests/tests_after_developing/18_test_worker_main.py
import unittest
import asyncio
from unittest.mock import AsyncMock, patch
import sys
import os

# 确保项目根目录在 PYTHONPATH 中
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from workers.main import main


class TestMainOrchestrator(unittest.IsolatedAsyncioTestCase):

    @patch("workers.main.start_email_scheduler", new_callable=AsyncMock)
    @patch("workers.main.start_im_scheduler", new_callable=AsyncMock)
    @patch("workers.main.fetch_loop", new_callable=AsyncMock)
    @patch("workers.main.tester_loop", new_callable=AsyncMock)
    async def test_main_startup_wiring(self, mock_tester, mock_fetch, mock_im, mock_email):
        """【测试 1】矩阵组网验证：验证四大战区协程是否被正确挂载，参数是否传递无误"""
        await main()

        mock_tester.assert_called_once()
        mock_fetch.assert_called_once()
        mock_im.assert_called_once()
        mock_email.assert_called_once()

        args, kwargs = mock_fetch.call_args
        self.assertEqual(kwargs.get('poll_interval'), 60)
        self.assertIsInstance(args[0], asyncio.Event)
        self.assertIsInstance(args[1], asyncio.Event)

    # 🚀 核心修复：把 sys.exit 拦截掉，防止它真的把测试框架杀掉
    @patch("workers.main.sys.exit")
    @patch("workers.main.start_email_scheduler")
    @patch("workers.main.start_im_scheduler")
    @patch("workers.main.fetch_loop")
    @patch("workers.main.tester_loop")
    async def test_main_graceful_shutdown_simulation(self, mock_tester, mock_fetch, mock_im, mock_email, mock_exit):
        """【测试 2】拔电源容灾演练：验证按下 Ctrl+C 后，主线程能否优雅地遣散所有子协程，不留僵尸进程"""

        async def infinite_loop_mock(*args, **kwargs):
            try:
                await asyncio.sleep(9999)
            except asyncio.CancelledError:
                pass

        mock_tester.side_effect = infinite_loop_mock
        mock_fetch.side_effect = infinite_loop_mock
        mock_im.side_effect = infinite_loop_mock
        mock_email.side_effect = infinite_loop_mock

        main_task = asyncio.create_task(main())

        await asyncio.sleep(0.05)

        self.assertTrue(mock_tester.called)
        self.assertTrue(mock_email.called)

        # 拔掉电源！
        main_task.cancel()

        try:
            await main_task
        except asyncio.CancelledError:
            pass

        # 🚀 核心断言：不仅没有卡死，我们还能精准验证它最后是否完美调用了 sys.exit(0)！
        mock_exit.assert_called_once_with(0)
        self.assertTrue(True, "矩阵成功完成优雅停机，没有发生进程级死锁！")


if __name__ == "__main__":
    unittest.main()