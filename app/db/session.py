# app/db/session.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ---------------------------------------------------------
# 1. 创建硬化版数据库引擎 (Engine)
# ---------------------------------------------------------
engine = create_engine(
    settings.DATABASE_URL,
    # 增加连接池大小，适应多 Worker 并发抓取与 AI 评分逻辑
    pool_size=15,
    max_overflow=25,

    # 活性能效检查：每次从池里取连接前先探测，确保连接没死 [2026 标准实践]
    pool_pre_ping=True,

    # 自动回收连接：周期性重建连接，防止数据库端强行断开导致的意外
    pool_recycle=3600,

    # 提高响应韧性：如果连接池满了，最多等 10 秒即报错，防止带崩前端
    pool_timeout=10
)

# ---------------------------------------------------------
# 2. 会话工厂配置
# ---------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


# ---------------------------------------------------------
# 3. 依赖注入函数 (get_db)
# ---------------------------------------------------------
def get_db():
    """
    FastAPI 依赖项：确保 Session 生命周期管理闭环。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        # 显式关闭连接，防止僵尸连接积累
        db.close()