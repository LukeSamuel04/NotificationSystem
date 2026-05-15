# app/api/api_router.py
from fastapi import APIRouter

# 1. 导入对内业务的端点 (Endpoints)
from app.api.endpoints import accounts
from app.api.endpoints import notifications
from app.api.endpoints import preference

# 2. 导入对外的 Webhook 接收点
from app.api.webhooks import instagram_hook

# 3. 实例化主集线器
api_router = APIRouter()

# ==========================================
# 🔌 挂载对内网关 (供前端 React 调用)
# ==========================================
api_router.include_router(accounts.router, prefix="/accounts", tags=["Accounts (账号资产)"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications (智能看板)"])

# 等你写好了 preferences.py，把这行也放开：
# api_router.include_router(preferences.router, prefix="/preferences", tags=["Preferences (偏好规则)"])


# ==========================================
# 📡 挂载对外网关 (供 Meta/第三方 调用)
# ==========================================
api_router.include_router(instagram_hook.router, prefix="/webhooks", tags=["Webhooks (外部监听)"])

# 💥 2. 加上这一行，把偏好设置的接口正式暴露出去！
api_router.include_router(preference.router, prefix="/preferences", tags=["preferences"])