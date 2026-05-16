# api/webhooks/instagram_hook.py
from fastapi import APIRouter, Query, HTTPException, Depends, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
import logging

# 引入数据库依赖和 Schema
from app.db.session import get_db
from app.schemas.notification import InstagramWebhookPayload

# 引入真正的入库业务逻辑
from app.services.instagram.webhook_manager import process_instagram_webhook

# 引入调度中心的紧急唤醒开关
from workers.ai.managers.im_scheduler import trigger_immediate_scan

logger = logging.getLogger(__name__)
router = APIRouter()

# 提醒：确保这与你在 Messenger API 设置页面填写的“验证口令”完全一致
VERIFY_TOKEN = "ai_priority_system_secret_2026"


# ==========================================
# 1. 握手验证接口 (GET 请求)
# ==========================================
@router.get("/instagram")
async def verify_instagram_webhook(
        hub_mode: str = Query(None, alias="hub.mode"),
        hub_challenge: str = Query(None, alias="hub.challenge"),
        hub_verify_token: str = Query(None, alias="hub.verify_token")
):
    """
    接收 Meta 的初次绑定验证请求（Messenger 和 Instagram 共用此逻辑）。
    """
    if hub_mode == "subscribe" and hub_verify_token == VERIFY_TOKEN:
        logger.info("✅ 验证成功！Meta 握手已完成。")
        return PlainTextResponse(content=hub_challenge, status_code=200)

    logger.warning("❌ 验证失败：Token 不匹配。")
    raise HTTPException(status_code=403, detail="Verification token mismatch")


# ==========================================
# 2. 接收动态接口 (POST 请求)
# ==========================================
@router.post("/instagram")
async def receive_instagram_message(
        payload: InstagramWebhookPayload,
        db: Session = Depends(get_db)
):
    """
    核心分拣中心：识别回声消息并决定是否启动 AI。
    """
    try:
        # 提取第一条核心动态 (Meta 的推送通常只包含一条有效动态)
        entry = payload.entry[0]
        messaging_event = entry.messaging[0]
        message = messaging_event.message

        if not message:
            return {"status": "no_message_content"}

        # 分拣回声消息
        is_echo = getattr(message, "is_echo", False)

        # 💥 用一个变量接收处理结果
        processed_successfully = False

        if is_echo:
            # --- 场景 A：回声消息 (Echo) ---
            logger.info(f"🔄 收到回声消息：我方已回复 -> {message.text[:20]}...")
            processed_successfully = await process_instagram_webhook(db, payload, is_from_me=True)
        else:
            # --- 场景 B：对方发来的真实新消息 ---
            sender_id = messaging_event.sender.id
            logger.info(f"👤 收到联系人({sender_id})新消息：{message.text}")
            processed_successfully = await process_instagram_webhook(db, payload, is_from_me=False)

        # 🚀 💥 核心联动：只有在账号激活并成功入库时，才唤醒 AI 调度器扫盘
        if processed_successfully:
            trigger_immediate_scan()
            logger.debug("🔔 已触发 AI 调度器唤醒信号！")

    except Exception as e:
        logger.error(f"⚠️ 处理 Webhook 载荷时发生异常: {e}")

    # 必须秒回 200，否则 Meta 会认为你宕机并重复推送
    return {"status": "success"}