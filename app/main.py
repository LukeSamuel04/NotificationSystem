# app/main.py

import time
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# 1. 导入你的路由收集器
from app.api.endpoints.collector import router as collector_router
# 2. 跨文件夹导入监听器的核心函数与配置
from workers.email_listener import check_inbox, POLL_INTERVAL


# ==========================================
# 模块一：后台守护线程逻辑 (The Daemon)
# ==========================================
def run_listener_loop():
    """
    专门为子线程准备的死循环函数。
    它会在后台默默运行，绝不会卡死主服务器的网络请求。
    """
    print(f"🚀 [后台线程] 邮件监听机器人已随服务器启动！每 {POLL_INTERVAL} 秒巡视一次...")
    while True:
        try:
            check_inbox()
        except Exception as e:
            print(f"❌ [后台线程] 监听器发生异常: {e}")
        time.sleep(POLL_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 生命周期管理器。
    用于在服务器启动时触发特定任务，在关闭时优雅清理。
    """
    # 【启动时】：挂载后台监听器
    print("⏳ 服务器正在启动，准备挂载后台邮件监听线程...")
    # daemon=True 极其关键：确保主程序（FastAPI）关闭时，这个死循环线程会被自动强杀，不会变成孤儿进程
    listener_thread = threading.Thread(target=run_listener_loop, daemon=True)
    listener_thread.start()

    yield  # 此时 FastAPI 开始正常处理前端的 HTTP 请求

    # 【关闭时】：优雅退出
    print("🛑 服务器正在关闭，监听器线程已随之终止...")


# ==========================================
# 模块二：FastAPI 核心配置 (The Core)
# ==========================================
# 初始化实例，并注入生命周期管理器
app = FastAPI(lifespan=lifespan)

#跨域解决方案：允许任何前端来访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 👈 关键点：允许所有来源（本地开发无敌模式）
    allow_credentials=False, # 👈 注意：如果 origin 是 "*", 这里必须是 False
    allow_methods=["*"],  # 允许所有方法 (GET, POST, OPTIONS, PATCH 等)
    allow_headers=["*"],  # 允许所有请求头
)


# 【全局异常拦截】：捕获 422 参数验证错误，返回标准 JSON 格式
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"⚠️ 参数验证错误: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )


# ==========================================
# 模块三：挂载路由 (The Routes)
# ==========================================
# 将 collector.py 里的接口挂载到主程序
app.include_router(collector_router)