from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# 1. 创建数据库引擎 (Engine)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True
)

# 2. 创建会话工厂 (SessionLocal)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 3. 创建依赖注入函数 (get_db)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()