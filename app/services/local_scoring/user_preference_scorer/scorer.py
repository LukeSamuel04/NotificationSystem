#app/services/local_scoring/user_preference_scorer/scorer.py
from typing import Dict, Any, List
from sqlalchemy.orm import Session

# 引入底层 ORM 模型
from app.models.user_preference import UserPreference


class UserPreferenceScorer:
    """
    用户偏好因子算子。
    基于独立规则表 (Scheme B)，支持多维度 (Sender, Topic, Domain) 匹配。
    采用“累乘模式”处理多条命中的规则。
    """

    def __init__(self, db: Session):
        self.db = db

    def calculate(
            self,
            account_id: str,
            platform: str,
            sender_id: str = None,
            current_topic: str = None,
            email_domain: str = None
    ) -> Dict[str, Any]:
        """
        计算综合偏好因子。
        逻辑：检索所有符合条件的规则，并将所有命中的 preference_factor 进行累乘。
        """
        final_factor = 1.0
        matched_details = []

        # 1. 预加载该账号在该平台（及 global）下的所有激活规则，减少数据库 IO 次数
        rules = self.db.query(UserPreference).filter(
            UserPreference.account_id == account_id,
            UserPreference.platform.in_([platform, "global"])
        ).all()

        if not rules:
            return {
                "preference_factor": 1.0,
                "matched_rules": []
            }

        for rule in rules:
            is_matched = False

            # 2. 多维度判定匹配逻辑

            # 维度 A：精准联系人 ID 匹配
            if rule.preference_type == "sender_id" and sender_id:
                if rule.target_value == sender_id:
                    is_matched = True

            # 维度 B：话题关键词模糊匹配 (针对 AI 提取出的 current_topic)
            elif rule.preference_type == "topic" and current_topic:
                if rule.target_value.lower() in current_topic.lower():
                    is_matched = True

            # 维度 C：Email 专属域名后缀匹配 (如 @bth.se)
            elif rule.preference_type == "email_domain" and email_domain:
                if rule.target_value.lower() == email_domain.lower():
                    is_matched = True

            # 3. 执行累乘逻辑
            if is_matched:
                final_factor *= rule.preference_factor
                matched_details.append({
                    "type": rule.preference_type,
                    "target": rule.target_value,
                    "factor": rule.preference_factor
                })

        # 4. 结果修约与边界保护
        # 确保因子不会变成负数，并保留 4 位小数保证计算精度
        final_factor = max(0.0, round(final_factor, 4))

        return {
            "preference_factor": final_factor,
            "matched_rules": matched_details
        }