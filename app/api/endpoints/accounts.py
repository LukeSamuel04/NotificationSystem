# app/api/endpoints/accounts.py
import logging
import httpx
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


# ==========================================
# 1. 列表获取 (Dashboard 渲染源)
# ==========================================
@router.get("/", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    """获取所有账号，用于前端 Dashboard 的状态展示"""
    return db.query(FetchAccount).all()


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
    # 1. 唯一性查重 (防止同一个 IG ID 或 Email 被重复绑定)
    existing_acc = db.query(FetchAccount).filter(
        FetchAccount.platform == account_in.platform,
        FetchAccount.platform_account_id == account_in.platform_account_id
    ).first()

    if existing_acc:
        raise HTTPException(status_code=400, detail="该外部账号 ID 已经绑定过了！")

    # 2. 准备配置字典 (适配 Pydantic v1/v2)
    config_dict = account_in.config.model_dump() if hasattr(account_in.config,
                                                            'model_dump') else account_in.config.dict()

    # 3. 💥 关键点：强验证拦截
    if account_in.platform == "email":
        # Email 验证：需要注入 username 进行 IMAP 登录尝试
        test_config = {**config_dict, "user": account_in.username}
        if not await EmailFetcher(test_config).test_connection():
            raise HTTPException(status_code=400, detail="邮件服务器连接失败，请检查 Host 或授权码。")

    elif account_in.platform == "instagram":
        # Instagram 验证：调用你刚刚写好的 AvailabilityTester
        # 它会拿着 Token 去向 Meta 官方请求，如果输入的是 "111"，这里会返回 False
        access_token = config_dict.get("access_token")
        tester = InstagramAvailabilityTester(
            meta_id=account_in.platform_account_id,
            access_token=access_token
        )

        if not await tester.test_connection():
            raise HTTPException(status_code=400, detail="Instagram 令牌或 ID 无效，Meta 拒绝连接。")

        logger.info(f"✅ Instagram 验证通过，准许入库: {account_in.username}")

    # 4. 实例化模型并持久化 (只有通过验证才能走到这里)
    new_account = FetchAccount(
        platform=account_in.platform,
        platform_account_id=account_in.platform_account_id,
        username=account_in.username,
        is_active=account_in.is_active,
        is_valid=True,  # 既然刚过验证，初始状态必为 True
        config=config_dict
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


# ==========================================
# 3. 更新账号 (逻辑合并 + 二次验证)
# ==========================================
@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_in: AccountUpdate, db: Session = Depends(get_db)):
    """更新账号：支持增量配置合并，并对变更后的配置重新发起探针"""
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

    # B. 如果账号是开启状态，且关键配置发生了变化，必须重新验证
    is_active_now = update_data.get("is_active", account.is_active)
    if is_active_now and "config" in update_data:
        if account.platform == "email":
            test_config = {**update_data["config"], "user": update_data.get("username", account.username)}
            if not await EmailFetcher(test_config).test_connection():
                raise HTTPException(status_code=400, detail="更新失败：新邮件配置无法连接服务器。")

        elif account.platform == "instagram":
            # 对更新后的 Token 再次验钞
            tester = InstagramAvailabilityTester(
                meta_id=account.platform_account_id,
                access_token=update_data["config"].get("access_token")
            )
            if not await tester.test_connection():
                raise HTTPException(status_code=400, detail="更新失败：新的 Instagram 令牌无效。")

    # C. 执行字段映射与更新
    for field, value in update_data.items():
        setattr(account, field, value)

    account.is_valid = True  # 验证通过后重置有效状态
    db.commit()
    db.refresh(account)
    return account


# ==========================================
# 4. 删除账号 (物理切断：不仅删库，还要拔线)
# ==========================================
@router.delete("/{account_id}")
async def delete_account(account_id: int, db: Session = Depends(get_db)):
    """绝对解绑：删除本地数据的同时，尝试调用 Meta API 撤销应用授权"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account.platform == "instagram":
        access_token = account.config.get("access_token")
        if access_token:
            try:
                async with httpx.AsyncClient() as client:
                    # 💥 向 Meta 发起 DELETE 请求，注销该 App 对此账号的权限
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
async def toggle_account(account_id: int, toggle_in: AccountToggle, db: Session = Depends(get_db)):
    """仅切换启用/禁用状态，不触发探针（用于前端 Switch 开关）"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account.is_active = toggle_in.is_active
    db.commit()
    db.refresh(account)
    return account