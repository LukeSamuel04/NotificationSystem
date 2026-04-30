from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.account import FetchAccount
# 💥 别忘了导入我们刚写的 AccountToggle
from app.schemas.account import AccountCreate, AccountResponse, AccountToggle
from workers.fetchers.email_fetcher import EmailFetcher

router = APIRouter()


# ==========================================
# 1. 核心业务接口：增删改查
# ==========================================

@router.post("/", response_model=AccountResponse)
async def create_account(account_in: AccountCreate, db: Session = Depends(get_db)):
    """
    新建抓取账号 (由前端齿轮配置弹窗调用)
    - 包含强制连通性验证
    - 验证通过后，is_valid 默认初始化为 True
    """
    # 1. 查重拦截
    existing_acc = db.query(FetchAccount).filter(
        FetchAccount.platform == account_in.platform,
        FetchAccount.username == account_in.username
    ).first()

    if existing_acc:
        raise HTTPException(status_code=400, detail="该平台的此账号已经绑定过了！")

    # 2. 强验证拦截网关 & 构造专属配置
    if account_in.platform == "email":
        host = account_in.config.host
        if not host:
            raise HTTPException(status_code=400, detail="邮件账号必须提供 host 地址！")

        temp_config = {
            "user": account_in.username,
            "password": account_in.password,
            "host": host
        }

        # 强制验证：连不上直接抛错打回，绝不入库
        is_valid = await EmailFetcher(temp_config).test_connection()
        if not is_valid:
            raise HTTPException(status_code=400, detail="账号或授权码验证失败，请检查配置或网络！")

    elif account_in.platform == "instagram":
        temp_config = account_in.config.model_dump() if hasattr(account_in.config,
                                                                'model_dump') else account_in.config.dict()
    else:
        raise HTTPException(status_code=400, detail=f"暂不支持验证的平台: {account_in.platform}")

    # 3. 入库 (能走到这里说明验证 100% 通过)
    new_account = FetchAccount(
        platform=account_in.platform,
        username=account_in.username,
        is_active=getattr(account_in, 'is_active', True),
        is_valid=True,  # 💥 新增：明确标记系统状态为健康
        config=temp_config
    )
    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    return new_account


@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(account_id: int, account_in: AccountCreate, db: Session = Depends(get_db)):
    """
    更新现有的账号配置 (由前端齿轮配置弹窗调用)
    - 包含强制连通性验证
    - 只有验证成功才会覆盖旧密码，并将 is_valid 重置为 True
    """
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    if account_in.platform == "email":
        host = account_in.config.host
        if not host:
            raise HTTPException(status_code=400, detail="邮件账号必须提供 host 地址！")

        new_config = {
            "user": account_in.username,
            "password": account_in.password,
            "host": host
        }

        # 强制验证：无论账号是否激活，只要修改了配置就必须验证
        is_valid = await EmailFetcher(new_config).test_connection()
        if not is_valid:
            raise HTTPException(status_code=400, detail="新授权码或配置验证失败，无法更新！")
    else:
        new_config = account_in.config.model_dump() if hasattr(account_in.config,
                                                               'model_dump') else account_in.config.dict()

    # 整体覆盖更新
    account.platform = account_in.platform
    account.username = account_in.username
    account.config = new_config
    account.is_active = getattr(account_in, 'is_active', True)
    account.is_valid = True  # 💥 新增：修改成功后，重置健康状态为 True

    db.commit()
    db.refresh(account)

    return account


@router.get("/", response_model=List[AccountResponse])
def get_accounts(db: Session = Depends(get_db)):
    """获取所有账号列表"""
    return db.query(FetchAccount).all()


@router.delete("/{account_id}")
def delete_account(account_id: int, db: Session = Depends(get_db)):
    """删除指定的账号"""
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    db.delete(account)
    db.commit()
    return {"message": "账号解除绑定成功"}


# ==========================================
# 2. 状态控制与监控接口 (UX 与 心跳专属)
# ==========================================

@router.patch("/{account_id}/toggle", response_model=AccountResponse)
async def toggle_account(account_id: int, toggle_in: AccountToggle, db: Session = Depends(get_db)):
    """
    一键启停账号 (由前端卡片外部 Switch 开关调用)
    - 💥 极轻量级接口：绝对不进行网络连通性验证
    - 仅翻转用户意愿状态 (is_active)
    """
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    account.is_active = toggle_in.is_active
    db.commit()
    db.refresh(account)
    return account


@router.post("/{account_id}/verify")
async def verify_account_connection(account_id: int, db: Session = Depends(get_db)):
    """
    独立的心跳验证接口 (由前端每分钟轮询调用)
    - 如果验证失败，会静默将数据库中的 is_valid 置为 False
    """
    account = db.query(FetchAccount).filter(FetchAccount.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")

    # 用户手动禁用的账号，直接跳过心跳检测，节约资源
    if not account.is_active:
        return {"status": "skipped", "message": "账号已禁用，跳过验证"}

    if account.platform == "email":
        is_valid = await EmailFetcher(account.config).test_connection()
        if not is_valid:
            # 💥 核心：发现失效，把数据库里的 is_valid 改为 False，然后再报错
            account.is_valid = False
            db.commit()
            raise HTTPException(status_code=400, detail="连接失效")

    # 验证如果顺畅通过，确保 is_valid 保持健康状态
    account.is_valid = True
    db.commit()

    return {"status": "ok", "message": "连接正常"}