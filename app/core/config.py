from pydantic_settings import BaseSettings
from pydantic import computed_field

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

    #AI推理配置
    HF_TOKEN: str
    AI_ALPHA: float

    #分类权重配置
    W_URGENT: float
    W_ACADEMIC: float
    W_HOUSING: float
    W_SOCIAL: float
    W_SPAM: float

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()