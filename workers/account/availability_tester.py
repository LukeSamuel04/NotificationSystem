# workers/account/availability_tester.py
import asyncio
import logging
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.account import FetchAccount

# 引入两个领域的“验钞机”
from workers.notification.fetchers.email_fetcher import EmailFetcher
from app.services.instagram.availability_tester import InstagramAvailabilityTester

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AvailabilityTester")

# 内存中维护每个账号的连续失败次数
FAIL_COUNTS = {}

# ==========================================
# 🆕 异步金丝雀探针 (非阻塞网络检查)
# ==========================================
async def is_internet_connected_async() -> bool:
    """
    第一关：使用异步连接测试公网连通性，绝不卡死主线程
    """
    try:
        # 尝试异步连接公共 DNS (Cloudflare)
        _, writer = await asyncio.wait_for(
            asyncio.open_connection("1.1.1.1", 53),
            timeout=3.0
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (asyncio.TimeoutError, OSError):
        return False

# ==========================================
# 核心巡检引擎
# ==========================================
async def tester_loop(stop_event: asyncio.Event):
    """
    纯后台挂载的异步巡检引擎：具备停机感知与非阻塞特性
    """
    logger.info("🩺 账号可用性测试引擎已就绪...")

    while not stop_event.is_set():
        # 1. 异步检查大网环境
        if not await is_internet_connected_async():
            logger.warning("⚠️ 公网探针失联，服务器可能处于断网状态，跳过本轮测试。")
        else:
            # 2. 开启数据库会话
            db: Session = SessionLocal()
            try:
                # 仅捞出活跃账号
                accounts = db.query(FetchAccount).filter(FetchAccount.is_active == True).all()

                for acc in accounts:
                    # 💥 架构升级：在外层根据平台动态组装探针实例
                    if acc.platform == "email":
                        # 兼容由于 Schema 升级被提取到外层的 username
                        test_config = {**acc.config, "user": acc.platform_account_id}
                        tester = EmailFetcher(test_config)
                        await check_single_account(acc, tester, db)

                    elif acc.platform == "instagram":
                        tester = InstagramAvailabilityTester(
                            meta_id=acc.platform_account_id,
                            access_token=acc.config.get("access_token")
                        )
                        await check_single_account(acc, tester, db)

                db.commit()
            except Exception as e:
                logger.error(f"❌ 测试引擎遇到数据库错误: {e}")
                db.rollback()
            finally:
                db.close()

        # 3. 动态休眠，随时响应主进程的 stop_event
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=60)
        except asyncio.TimeoutError:
            pass

    logger.info("🛑 账号巡检探针已安全下线。")

async def check_single_account(acc: FetchAccount, tester_instance, db: Session):
    """
    分类探测与防抖容错逻辑 (拥抱多态)
    """
    try:
        if acc.id not in FAIL_COUNTS:
            FAIL_COUNTS[acc.id] = 0

        # 💥 核心改动：直接调用传入实例的测试方法
        is_success = await tester_instance.test_connection()

        if is_success:
            FAIL_COUNTS[acc.id] = 0
            if not acc.is_valid:
                acc.is_valid = True
                logger.info(f"✅ 账号 [{acc.platform}] {acc.username} 恢复健康。")
        else:
            FAIL_COUNTS[acc.id] += 1
            logger.warning(f"⚠️ 账号 [{acc.platform}] {acc.username} 验证失败 ({FAIL_COUNTS[acc.id]}/3)")

            # 连续 3 次失败判定为失效
            if FAIL_COUNTS[acc.id] >= 3:
                acc.is_valid = False
                logger.error(f"🚫 账号 [{acc.platform}] {acc.username} 确认失联，标记为失效。")
                acc.is_active = False

    except Exception as e:
        logger.error(f"执行账号 {acc.username} 检查时发生异常: {e}")