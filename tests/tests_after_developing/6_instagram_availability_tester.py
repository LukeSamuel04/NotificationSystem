# tests/tests_after_developing/6_instagram_availability_tester.py
import unittest
from unittest.mock import patch, AsyncMock, MagicMock
import httpx

# 导入待测的一次性特种探针类
from app.services.instagram.availability_tester import InstagramAvailabilityTester


class TestInstagramAvailabilityTester(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        """测试前置准备：初始化一套虚拟的测试账号资产"""
        self.meta_id = "17841479965622632"
        self.token = "mock_meta_long_lived_token_2026"
        self.tester = InstagramAvailabilityTester(meta_id=self.meta_id, access_token=self.token)

    @patch("app.services.instagram.availability_tester.httpx.AsyncClient")
    async def test_test_connection_success(self, mock_client_cls):
        """【测试 1】验证成功场景：当 Meta 返回 200 且数据完整时，探针精准返回 True"""
        # 1. 模拟 httpx.AsyncClient 的异步上下文管理器行为
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # 2. 模拟 Meta 官方健康的 JSON 报文响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "17841479965622632",
            "username": "luke_samuel04"
        }
        mock_client.get.return_value = mock_response

        # 3. 触发探针敲门动作
        result = await self.tester.test_connection()

        # 4. 全链路断言判定
        self.assertTrue(result)
        # 严格验证探针向 Meta 发起请求时的 URL 拼装和参数组装是否符合 Graph API 契约
        mock_client.get.assert_called_once_with(
            "https://graph.facebook.com/v25.0/17841479965622632",
            params={
                "access_token": "mock_meta_long_lived_token_2026",
                "fields": "id,username"
            }
        )

    @patch("app.services.instagram.availability_tester.httpx.AsyncClient")
    async def test_test_connection_token_expired(self, mock_client_cls):
        """【测试 2】验证权限失效：当用户在手机端改了密码导致 Token 变成死包(400/401)时，探针敏锐捕获返回 False"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # 模拟 Meta 网关无情拒绝的响应
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": {"message": "The access token could not be decrypted", "type": "OAuthException"}}'
        mock_client.get.return_value = mock_response

        # 触发动作
        result = await self.tester.test_connection()

        # 断言判定：必须安全返回 False，用于触发 Manager 的连续失败计数防抖
        self.assertFalse(result)

    @patch("app.services.instagram.availability_tester.httpx.AsyncClient")
    async def test_test_connection_network_crash(self, mock_client_cls):
        """【测试 3】验证大网崩溃：当服务器遭遇海外机房断网、DNS 劫持抛出 httpx 异常时，弹性容错返回 False"""
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        # 模拟 httpx 在点对点通信时直接发生网络连接超时或断网炸裂
        mock_client.get.side_effect = httpx.RequestError("Connection timed out to graph.facebook.com")

        # 触发动作
        result = await self.tester.test_connection()

        # 断言判定：顶层 try...except httpx.RequestError 拦截盾牌必须生效，安全化解红爆并返回 False
        self.assertFalse(result)

    async def test_test_connection_missing_parameters(self):
        """【测试 4】验证防御性边界：当初始化传入的 meta_id 或 token 本身就是空值时，光速熔断返回 False"""
        # 故意制造一个残缺的无效探针
        broken_tester = InstagramAvailabilityTester(meta_id="", access_token=None)

        result = await broken_tester.test_connection()

        # 断言判定：第一层 if 守卫应当直接拦截，根本不需要浪费 CPU 去创建 AsyncClient 发起网络开销
        self.assertFalse(result)


# 💥 挂载标准单元测试启动入口，允许在 IDE 中直接一键点击点击运行
if __name__ == "__main__":
    unittest.main()