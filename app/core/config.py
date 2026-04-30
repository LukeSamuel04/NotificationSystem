import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

# 💥 防弹技巧：利用当前文件的绝对路径，反推出项目根目录
# __file__ 是 app/core/config.py
# 向上三层 dirname 刚好是 notification_system 根目录
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_PATH = os.path.join(ROOT_DIR, ".env")


class Settings(BaseSettings):
    # DB连接配置
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # AI推理配置
    HF_TOKEN: str
    AI_ALPHA: float

    # 分类权重配置
    W_URGENT: float
    W_ACADEMIC: float
    W_HOUSING: float
    W_SOCIAL: float
    W_SPAM: float

    # 💥 Pydantic V2 标准写法：取代原来的 class Config
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,  # 使用绝对路径，彻底告别找不到文件的问题
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()