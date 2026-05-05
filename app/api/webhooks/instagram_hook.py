from fastapi import APIRouter, Request, BackgroundTasks, Query, HTTPException
from fastapi.responses import PlainTextResponse

# 假设这是你的底层业务逻辑（目前可以先注释掉，等实际写了再引入）
# from app.services.instagram_service import process_incoming_message

router = APIRouter()

# ⚠️ 这个令牌极其重要！等会要在 Meta 后台填入一模一样的字符串
# 建议以后放到 .env 文件里，现在测试可以直接硬编码
VERIFY_TOKEN = "ai_priority_system_secret_2026"


# ==========================================
# 1. 握手验证接口 (GET 请求) - Meta 专属查岗通道
# ==========================================
@router.get("/instagram")
async def verify_instagram_webhook(
        hub_mode: str = Query(None, alias="hub.mode"),
        hub_challenge: str = Query(None, alias="hub.challenge"),
        hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    接收 Meta 的初次绑定验证请求。
    """
    # 检查模式和令牌是否匹配
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        print("✅ 验证成功！Meta 确认了你的服务器身份。")
        # 必须返回原封不动的 challenge 数字，且必须是 200 状态码
        return PlainTextResponse(content=hub_challenge, status_code=200)

    print("❌ 验证失败：提供的 Token 不匹配。")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


# ==========================================
# 2. 接收私信接口 (POST 请求) - 真实数据入口
# ==========================================
@router.post("/instagram")
async def receive_instagram_message(
        request: Request,
        background_tasks: BackgroundTasks
):
    """
    接收用户发给 Instagram 商业号的真实私信。
    """
    try:
        # 瞬间拿到 Meta 推送的 JSON 盒子
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format")

    print("\n📬 收到新动态！原始数据如下：")
    # 测试阶段：直接打印出来看看长什么样
    import json
    print(json.dumps(payload, indent=2))

    # 核心架构：把解析、调用大模型打分等耗时操作，扔给后台任务
    # 确保主线程不会被阻塞，从而能瞬间给 Meta 返回 200 OK
    # background_tasks.add_task(process_incoming_message, payload)

    # 必须快速返回，让 Meta 知道你收到了，停止重试机制
    return {"status": "success"}