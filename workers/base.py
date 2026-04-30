# workers/fetchers/base.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseFetcher(ABC):
    """
    所有抓取器（Email, SNS, etc.）的抽象基类。
    它像是一个“合同”，规定了所有子类必须具备的功能。
    """

    def __init__(self, account_config: Dict[str, Any]):
        """
        初始化时传入账号配置。
        account_config 应该包含：用户名、密码/授权码、服务器地址等。
        """
        self.config = account_config

    @abstractmethod
    async def test_connection(self) -> bool:
        """
        [必须实现] 防脏数据探针。
        用于在绑定账号时，仅测试握手连接，不抓取数据。
        返回 True 表示配置有效，False 表示无效。
        """
        pass

    @abstractmethod
    async def fetch_new(self) -> List[Dict[str, Any]]:
        """
        [必须实现] 核心抓取逻辑。
        返回格式必须统一，例如：
        [
            {
                "platform": "email",
                "msg_id": "123",
                "sender": "father@work.com",
                "subject": "Server Down",
                "content": "Check the maintenance logs..."
            }
        ]
        """
        pass

    @abstractmethod
    async def mark_as_processed(self, msg_id: Any):
        """
        [必须实现] 标记为已处理。
        防止下次运行 fetch_new 时又把同一条消息抓回来。
        """
        pass

    def validate_config(self) -> bool:
        """
        [可选] 本地字段静态校验。
        用于检查 config 里的关键字段是否缺失，避免无意义的网络请求。
        """
        return all(key in self.config for key in ["user", "password"])