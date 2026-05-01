# app/main.py
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

# 路由导入
from app.api.endpoints import accounts, notifications


# ==========================================
# 🆕 1. 资源生命周期管理器 (Lifespan)
# ==========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    管理系统启动与关闭时的资源行为。
    能有效防止 PyCharm 停止后子进程变“僵尸”的问题。
    """
    # 【启动阶段：系统推油】
    print("🚀 Notification System 正在启动...")

    # 存储后台任务的引用，方便后续清理
    app.state.background_tasks = []

    # 💡 如果你之后要启动那三个 Worker，应该在这里启动：
    # from workers.fetch_manager import fetch_manager
    # from workers.ai_manager import ai_manager
    # from workers.availability_tester import availability_tester

    # task_fetch = asyncio.create_task(fetch_manager.run())
    # task_ai = asyncio.create_task(ai_manager.run())
    # task_verify = asyncio.create_task(availability_tester.run())

    # app.state.background_tasks.extend([task_fetch, task_ai, task_verify])

    yield  # --- 这里是 API 提供服务的生命周期 ---

    # 【关闭阶段：安全撤退】
    print("🛑 正在接收关闭信号，准备清理资源...")

    # 💥 核心：显式取消所有后台任务，不留僵尸
    if hasattr(app.state, "background_tasks"):
        for task in app.state.background_tasks:
            task.cancel()

        # 等待所有任务确认取消（给它们一点处理善后的时间）
        await asyncio.gather(*app.state.background_tasks, return_exceptions=True)

    print("✅ 所有后台任务已安全取消，资源清理完毕，进程退出。")


# ==========================================
# 2. 初始化 FastAPI 实例 (挂载 lifespan)
# ==========================================
app = FastAPI(
    title="Notification System API",
    version="2.0",
    lifespan=lifespan
)

# ==========================================
# 3. 全局中间件配置
# ==========================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# 4. 全局异常拦截器
# ==========================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"⚠️ 参数验证错误: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# ==========================================
# 5. 挂载核心业务路由
# ==========================================
app.include_router(accounts.router, prefix="/api/accounts", tags=["账号管理"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)