# app/services/instagram/availability_tester.py
# app/services/instagram/availability_tester.py
from utils.proxy_helper import inject_local_proxy
inject_local_proxy()
import httpx
import logging
import asyncio
import os
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger("InstagramProbe")

# 💥 规范：在文件加载时，优先把本地环境中的配置变量加载进来
load_dotenv(find_dotenv(), override=True)


class InstagramAvailabilityTester:
    def __init__(self, meta_id: str, access_token: str):
        """
        初始化 Instagram 探针
        :param meta_id: 外部平台的账号 ID (platform_account_id)
        :param access_token: 用户授权的长效访问令牌
        """
        self.meta_id = meta_id
        self.token = access_token
        # 保持使用 Meta Graph API 的稳定演进版本
        self.base_url = "https://graph.facebook.com/v25.0"

    async def test_connection(self) -> bool:
        """
        核心探针逻辑：拿着 Token 去 Meta 家敲门，测试有效性
        """
        if not self.token or not self.meta_id:
            logger.error("❌ Instagram 探针验证失败: 缺少依赖的 meta_id 或 access_token")
            return False

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 访问该账号的 Graph API 节点，请求最基础的 id 字段来验证 Token
                url = f"{self.base_url}/{self.meta_id}"
                response = await client.get(
                    url,
                    params={
                        "access_token": self.token,
                        "fields": "id,username"  # 顺带查一下 username，方便日志辨认
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    username = data.get('username', '未知昵称')
                    logger.info(f"✅ Instagram 探针验证通过: 成功连接到账号 [{username}] (ID: {self.meta_id})")
                    return True
                else:
                    # 可能是 Token 过期、权限被撤销，或者 ID 填错了
                    logger.warning(f"⚠️ Instagram 探针被 Meta 拒绝 (状态码 {response.status_code}): {response.text}")
                    return False

        except httpx.RequestError as e:
            logger.error(f"🌐 Instagram 探针网络请求异常 (可能是断网或 DNS 问题): {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Instagram 探针发生未知错误: {e}")
            return False


# ==========================================
# 🚀 独立本地快速验证验证模块 (已彻底消除硬编码)
# ==========================================
if __name__ == "__main__":
    # 配置基础的日志输出格式，方便在控制台查看
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


    async def run_local_debug():
        print("\n--- ⏳ 开始执行 Instagram 探针本地安全调试 ---")

        # 💥 重构精髓：从 .env 文件中动态读取测试凭证，绝不将真实 Token 遗留在代码树中
        test_meta_id = os.getenv("Test_meta_id")
        test_token = os.getenv("Public_page_token_new")

        if not test_meta_id or not test_token:
            logger.error(
                "❌ 调试终止：未在本地 .env 文件中检测到 'DEBUG_INSTAGRAM_META_ID' 或 'DEBUG_INSTAGRAM_TOKEN'。\n"
                "👉 请在项目根目录的 .env 中补齐配置后再点击一键运行。"
            )
            return

        tester = InstagramAvailabilityTester(meta_id=test_meta_id, access_token=test_token)
        result = await tester.test_connection()

        print(f"--- 🏁 调试结束: 探针反馈状态 ➔ {'通过 (True)' if result else '失败 (False)'} ---\n")


    # 启动调试异步引擎
    asyncio.run(run_local_debug())