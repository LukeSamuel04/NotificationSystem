# app/services/instagram/availability_tester.py
import httpx
import logging
import asyncio

logger = logging.getLogger(__name__)


class InstagramAvailabilityTester:
    def __init__(self, meta_id: str, access_token: str):
        """
        初始化 Instagram 探针
        :param meta_id: 外部平台的账号 ID (platform_account_id)
        :param access_token: 用户授权的长效访问令牌
        """
        self.meta_id = meta_id
        self.token = access_token
        # 建议使用 v19.0 或更新的稳定版本
        self.base_url = "https://graph.facebook.com/v25.0"

    async def test_connection(self) -> bool:
        """
        核心探针逻辑：拿着 Token 去 Meta 家敲门，测试有效性
        """
        if not self.token or not self.meta_id:
            logger.error("❌ Instagram 探针失败: 缺少 meta_id 或 access_token")
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
# 🚀 独立测试模块 (方便你直接跑通)
# ==========================================
if __name__ == "__main__":
    # 配置基础的日志输出格式，方便在控制台查看
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


    async def run_test():
        print("--- 开始测试 Instagram 探针 ---")

        # TODO: 把这里的测试数据换成你真实的 Meta ID 和 Token
        TEST_META_ID = "17841479965622632"
        TEST_TOKEN = "EAAU2w0HcsFkBRdrHe6ZBRYO6MhlW7CzCzwgIZApFHux1O54GwzpYUCY7A758nNfUK8qSnQz3tijx6qo4Fjdr60rcSLd4DUQHZAsZCmGPBGsyZA2uzrf5xfRoYHT8l7PxyPT3g3vrNp3ZCQzeUIkYymjWg4lNsCFDaHptgRNEeGBUAmY9epJQ77ZAN7ZCytNxAYhZAD2bRvBmtZCS7ZBLis103ZA0ZBZCccZB21KmkOUB63VFrIATkGf"
        tester = InstagramAvailabilityTester(meta_id=TEST_META_ID, access_token=TEST_TOKEN)
        result = await tester.test_connection()

        print(f"--- 测试结果: {'通过 (True)' if result else '失败 (False)'} ---")


    # 运行测试
    asyncio.run(run_test())