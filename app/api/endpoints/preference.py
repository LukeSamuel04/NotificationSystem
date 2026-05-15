# app/api/endpoints/preference.py
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user_preference import UserPreference
from app.schemas.user_preference import (
    UserPreferenceCreate,
    UserPreferenceResponse,
    UserPreferenceUpdate
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ==========================================
# 1. 获取规则列表 (偏好设置面板渲染源)
# ==========================================
@router.get("/", response_model=List[UserPreferenceResponse])
def get_preferences(
        account_id: str = Query(..., description="所属系统账号 ID"),
        platform: Optional[str] = None,
        db: Session = Depends(get_db)
):
    """
    获取某个账号下的所有偏好规则。
    前端通过 account_id 来加载对应的“调教规则列表”。
    """
    query = db.query(UserPreference).filter(UserPreference.account_id == account_id)

    if platform:
        query = query.filter(UserPreference.platform == platform)

    return query.all()


# ==========================================
# 2. 新增偏好规则 (用户自定义干预)
# ==========================================
@router.post("/", response_model=UserPreferenceResponse)
def create_preference(
        pref_in: UserPreferenceCreate,
        db: Session = Depends(get_db)
):
    """
    用户在前端手动添加一条规则。
    例如：针对 'bth.se' 域名的邮件赋予 2.0 的权重因子。
    """
    # 检查是否已存在完全相同的规则 (防止重复定义)
    existing = db.query(UserPreference).filter_by(
        account_id=pref_in.account_id,
        platform=pref_in.platform,
        preference_type=pref_in.preference_type,
        target_value=pref_in.target_value
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail="该偏好规则已经存在，请直接修改原有规则")

    new_pref = UserPreference(
        account_id=pref_in.account_id,
        platform=pref_in.platform,
        preference_type=pref_in.preference_type,
        target_value=pref_in.target_value,
        preference_factor=pref_in.preference_factor
    )

    db.add(new_pref)
    db.commit()
    db.refresh(new_pref)

    logger.info(f"✨ 新增偏好规则: {pref_in.target_value} -> {pref_in.preference_factor}x")
    return new_pref


# ==========================================
# 3. 修改规则内容 (动态权重微调)
# ==========================================
@router.patch("/{preference_id}", response_model=UserPreferenceResponse)
def update_preference(
        preference_id: int,
        pref_in: UserPreferenceUpdate,
        db: Session = Depends(get_db)
):
    """
    用户在前端通过滑动条修改权重因子，或编辑匹配的关键词。
    """
    pref = db.query(UserPreference).filter(UserPreference.id == preference_id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="规则未找到")

    update_data = pref_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(pref, field, value)

    db.commit()
    db.refresh(pref)
    return pref


# ==========================================
# 4. 删除规则 (撤销人工干预)
# ==========================================
@router.delete("/{preference_id}")
def delete_preference(
        preference_id: int,
        db: Session = Depends(get_db)
):
    """
    用户点击“删除”图标，彻底移除该条人工干预规则。
    """
    pref = db.query(UserPreference).filter(UserPreference.id == preference_id).first()
    if not pref:
        raise HTTPException(status_code=404, detail="规则未找到")

    db.delete(pref)
    db.commit()

    logger.info(f"🗑️ 已移除偏好规则 ID: {preference_id}")
    return {"status": "success", "message": "规则已删除"}