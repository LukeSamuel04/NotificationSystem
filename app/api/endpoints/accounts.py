# app/api/endpoints/accounts.py
import logging
import httpx
import copy
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.account import FetchAccount
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate, AccountToggle

# 🛡️ 核心验证逻辑引入
from workers.notification.fetchers.email_fetcher import EmailFetcher
from app.services.instagram.availability_tester import InstagramAvailabilityTester

logger = logging.getLogger(__name__)
router = APIRouter()


def _mask_account(account: FetchAccount) -> AccountResponse:
    """
    🔐 核心安全屏障：数据脱敏遮罩
    拦截 ORM 对象，抹除其中的敏感 Token 和密码，然后再返回给前端。
    绝对不能让密码和完整 token 在浏览器的 Network 面板里裸奔！
    """
    account_dict = {
        "id": account.id,
        "platform_account_id": account.platform_account_id,
        "platform": account.platform,
        "username": account.username,
        "is_valid": account.is_valid,
        "is_active": account.is_active,
        "config": {}
    }

    if account.config:
        safe_config = copy.deepcopy(account.config)
        # 1. 抹除邮件密码
        if "password" in safe_config:
            safe_config["password"] = "********"

        # 2. 截断 Instagram Token (只保留前10位用于前端辨认)
        if "access_token" in safe_config:
            token = safe_config["access_token"]
            safe_config["access_token"] = f"{token[:10]}..." if token else ""

        # 3. 截断 WhatsApp API Key (若有)
        if "api_key" in safe_config:
            api_key = safe_config["api_key"]
            safe_config["api_key"] = f"{api_key[:10]}..." if api_key else ""

        account_dict["config"] = safe_config

    return AccountResponse(**account_dict)


# ==========================================
# 1. 列表获取 (Dashboard 渲染源)
# ==========================================
@router.get("/", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    """获取所有账号，用于前端 Dashboard 的状态展示"""
    accounts = db.query(FetchAccount).all()
    return [_mask_account(acc) for acc in accounts]


# ==========================================
# 2. 新建账号 (核心防火墙：验钞不通过不入库)
# ==========================================
@router.post("/", response_model=AccountResponse)
async def create_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    """
    新建账号链路：
    1. 唯一性冲突检查 (platform + platform_account_id)
    2. 调用第三方平台探针进行“真伪/存活”验证
    3. 验证通过后持久化到数据库
    """
    existing_acc = db.query(FetchAccount).filter(
        FetchAccount.platform == account_in.platform,
        FetchAccount.platform_account_id == account_in.platform_account_id
    ).first()

    if existing_acc:
        raise HTTPException(status_code=400, detail="该外部账号 ID 已经绑定过了！")

    config_dict = account_in.config.model_dump() if hasattr(account_in, 'model_dump') else account_in.config.dict()

    if account_in.platform == "email":
        test_config = {**config_dict, "user": account_in.platform_account_id}
        if not await EmailFetcher(test_config).test_connection():
            raise HTTPException(status_code=400, detail="邮件服务器连接失败，请检查 Host 或授权码。")

    elif account_in.platform == "instagram":
        access_token = config_dict.get("access_token")
        tester = InstagramAvailabilityTester(
            meta_id=account_in.platform_account_id,
            access_token=access_token
        )
        if not await tester.test_connection():
            raise HTTPException(status_code=400, detail="Instagram 令牌或 ID 无效，Meta 拒绝连接。")
        logger.info(f"✅ Instagram 验证通过，准许入库: {account_in.username}")

    new_account = FetchAccount(
        platform=account_in.platform,
        platform_account_id=account_in.platform_account_id,
        username=account_in.username,
        is_active=account_in.is_active,
        is_valid=True,
        config=config_dict
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return _mask_account(new_account)


# ==========================================
# 3. 更新账号 (💥 方案 2 鲁棒性升级版)
# ==========================================
@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: str, account_in: AccountUpdate, db: Session = Depends(get_db)):
    """更新账号：支持增量配置合并，并对变更后的配置无视状态强制重新发起探针"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    update_data = account_in.model_dump(exclude_unset=True) if hasattr(account_in, 'model_dump') else account_in.dict(
        exclude_unset=True)
    current_config = dict(account.config) if account.config else {}

    # A. 如果更新包含 config，进行深度合并
    if "config" in update_data:
        merged_config = {**current_config, **update_data["config"]}
        update_data["config"] = merged_config

    # 💥 B. 核心修复：重新构建探针校验的触发边界 (方案 2)
    # 只要满足以下任一条件，后端必须无条件启动 EmailFetcher 探针：
    # 条件 1：用户修改了敏感配置（如密码授权码、Token改变）-> 必须验真新配置
    # 条件 2：用户试图将账号状态从“禁用”切回“启用” -> 必须验真已有配置，确保能安全开启后台巡检
    config_changed = "config" in update_data
    activating = update_data.get("is_active") is True and not account.is_active

    if config_changed or activating:
        # 获取待测试的最终配置字典（如果改变了用合并后的，没变用数据库原有的）
        config_to_test = update_data.get("config", account.config) or {}

        if account.platform == "email":
            test_config = {**config_to_test, "user": account.platform_account_id}
            if not await EmailFetcher(test_config).test_connection():
                raise HTTPException(status_code=400, detail="更新失败：邮件服务器连接失败，请检查授权码或主机地址。")

        elif account.platform == "instagram":
            tester = InstagramAvailabilityTester(
                meta_id=account.platform_account_id,
                access_token=config_to_test.get("access_token")
            )
            if not await tester.test_connection():
                raise HTTPException(status_code=400, detail="更新失败：Instagram 长期令牌或 Meta ID 校验失败。")

        # 💥 只有真正走完上面且连接成功的安全请求，才有资格被标记为合法有效
        account.is_valid = True

    # C. 执行字段映射与更新
    for field, value in update_data.items():
        setattr(account, field, value)

    # 💥 核心修复：移除了原本放在函数末尾的盲目 `account.is_valid = True`
    # 如果用户仅仅是修改了无伤大雅的 `username`，账号可用性状态将保持原有状态不变
    db.commit()
    db.refresh(account)

    return _mask_account(account)


# ==========================================
# 4. 删除账号 (物理切断)
# ==========================================
@router.delete("/{account_id}")
async def delete_account(account_id: str, db: Session = Depends(get_db)):
    """绝对解绑：删除本地数据的同时，尝试调用 Meta API 撤销应用授权"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.platform == "instagram":
        access_token = account.config.get("access_token")
        if access_token:
            try:
                async with httpx.AsyncClient() as client:
                    meta_url = f"https://graph.facebook.com/v19.0/{account.platform_account_id}/permissions"
                    response = await client.delete(meta_url, params={"access_token": access_token})
                    if response.status_code == 200:
                        logger.info(f"✅ Meta 授权已撤销: {account.platform_account_id}")
            except Exception as e:
                logger.error(f"🌐 尝试撤销 Meta 授权时发生异常: {e}")

    db.delete(account)
    db.commit()
    return {"message": "账号已彻底移除并解除授权"}


# ==========================================
# 5. 快速状态切换 (Toggle 开关)
# ==========================================
@router.patch("/{account_id}/toggle", response_model=AccountResponse)
async def toggle_account(account_id: str, toggle_in: AccountToggle, db: Session = Depends(get_db)):
    """仅切换启用/禁用状态，不触发探针（用于前端 Switch 开关）"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account.is_active = toggle_in.is_active
    db.commit()
    db.refresh(account)

    return _mask_account(account)