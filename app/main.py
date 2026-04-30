from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from app.api.endpoints import notifications
from fastapi.responses import RedirectResponse
# 核心路由导入
from app.api.endpoints import accounts

# ==========================================
# 1. 初始化 FastAPI 实例
# ==========================================
app = FastAPI(title="Notification System API", version="2.0")

# ==========================================
# 2. 全局中间件配置
# ==========================================
# 跨域解决方案：允许任何前端来访问 (本地开发无敌模式)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 3. 全局异常拦截器
# ==========================================
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """
    捕获 422 参数验证错误，将乱码或长篇大论的报错转化为清晰的 JSON
    """
    print(f"⚠️ 参数验证错误: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors()}
    )

# ==========================================
# 4. 挂载核心业务路由
# ==========================================
app.include_router(accounts.router, prefix="/api/accounts", tags=["账号管理"])
print('Notification router will be used!')
# 现在的挂载极其规范，和 accounts 保持完美队形
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    # 不在乎图标，直接返回空响应
    from fastapi import Response
    return Response(status_code=204)