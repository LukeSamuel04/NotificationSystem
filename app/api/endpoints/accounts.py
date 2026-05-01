from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import asyncio

from app.db.session import get_db
from app.models.account import FetchAccount
from app.schemas.account import AccountCreate, AccountResponse, AccountUpdate, AccountToggle
from workers.notification.fetchers.email_fetcher import EmailFetcher

router = APIRouter()


# ==========================================
# 1. 列表获取
# ==========================================
@router.get("/", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    """获取所有账号列表"""
    return db.query(FetchAccount).all()


# ==========================================
# 2. 新建账号 (强验证)
# ==========================================
@router.post("/", response_model=AccountResponse)
async def create_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    """新建账号：验证通过后方可入库"""
    # 1. 查重
    existing_acc = db.query(FetchAccount).filter(
        FetchAccount.platform == account_in.platform,
        FetchAccount.username == account_in.username
    ).first()
    if existing_acc:
        raise HTTPException(status_code=400, detail="该账号已经绑定过了！")

    # 2. 准备配置字典并压入凭证
    config_dict = account_in.config.dict() if hasattr(account_in.config, 'dict') else account_in.config
    config_dict.update({
        "user": account_in.username,
        "password": account_in.password  # 密码被收纳进 JSON 字段
    })

    # 3. 强验证拦截
    if account_in.platform == "email":
        is_valid = await EmailFetcher(config_dict).test_connection()
        if not is_valid:
            raise HTTPException(status_code=400, detail="验证失败！请检查授权码或服务器配置。")

    # 4. 实例化模型 (注意：这里不再传入不存在的 password 参数)
    new_account = FetchAccount(
        platform=account_in.platform,
        username=account_in.username,
        # ❌ 移除了 password=account_in.password，因为 Model 里没这一列
        is_active=getattr(account_in, 'is_active', True),
        is_valid=True,
        config=config_dict
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)
    return new_account


# ==========================================
# 3. 更新账号 (增量合并 + 验证)
# ==========================================
@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_in: AccountUpdate, db: Session = Depends(get_db)):
    """更新账号：防止 JSON 覆盖，支持局部更新"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    update_data = account_in.dict(exclude_unset=True)
    current_config = dict(account.config) if account.config else {}

    if account.platform == "email":
        if "config" in update_data:
            new_host = update_data["config"].get("host")
            if new_host and new_host != current_config.get("host"):
                raise HTTPException(status_code=400, detail="禁止修改服务器地址 (Host)")

        # ⚡ 准备测试快照：合并新旧数据
        test_config = current_config.copy()
        if "username" in update_data: test_config["user"] = update_data["username"]
        if "password" in update_data: test_config["password"] = update_data["password"]
        if "config" in update_data: test_config.update(update_data["config"])

        # 🚀 只有在“开启”状态下更新才触发网络验证
        is_active_now = update_data.get("is_active", account.is_active)
        if is_active_now:
            is_valid = await EmailFetcher(test_config).test_connection()
            if not is_valid:
                raise HTTPException(status_code=400, detail="更新失败：新配置无法连接服务器。")

        # 验证通过后，将合并后的快照存入 update_data 的 config 键中
        update_data["config"] = test_config

    # 💥 关键点：从 update_data 中移除 password 键
    # 因为 password 已经合并到 config 字典里了，如果不移除，下面的 setattr 会报错
    update_data.pop("password", None)

    # 执行字段更新
    for field, value in update_data.items():
        setattr(account, field, value)

    account.is_valid = True
    db.commit()
    db.refresh(account)
    return account


# ==========================================
# 4. 删除账号
# ==========================================
@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(account)
    db.commit()
    return {"message": "账号解除绑定成功"}


# ==========================================
# 5. 状态切换 (Patch)
# ==========================================
@router.patch("/{account_id}/toggle", response_model=AccountResponse)
async def toggle_account(account_id: int, toggle_in: AccountToggle, db: Session = Depends(get_db)):
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account.is_active = toggle_in.is_active
    db.commit()
    db.refresh(account)
    return account