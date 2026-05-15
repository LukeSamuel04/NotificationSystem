# app/services/local_scoring/priority_orchestrator.py
import math
from typing import Dict, Any
from sqlalchemy.orm import Session

# 引入底层算子与模型
from app.services.local_scoring.poission_urgency_scorer.im.scorer import IMPoissonUrgencyScorer
from app.services.local_scoring.user_preference_scorer.scorer import UserPreferenceScorer
from app.models.im_session import IMSessionState
from app.models.analysis_payload import AnalysisPayload  # 💥 新增冷数据模型


class PriorityOrchestrator:
    def __init__(self, db: Session):
        self.db = db
        # 初始化泊松算子与用户偏好算子
        self.poisson_scorer = IMPoissonUrgencyScorer(db)
        self.pref_scorer = UserPreferenceScorer(db)

    def resolve_priority(
            self,
            account_id: str,
            notification_id: int,  # 💥 传入消息 ID 以实现每条消息的特征存证
            external_sender_id: str,
            ai_score: int,
            current_topic: str,
            platform: str = "instagram"
    ) -> Dict[str, Any]:
        """
        核心编排逻辑：聚合多路因子，执行非线性平方根平滑，并完成冷热数据分离持久化。
        """
        # 1. 提取泊松因子 (仅针对 IM 平台)
        f_poisson = 1.0
        if platform == "instagram":
            poisson_res = self.poisson_scorer.calculate(external_sender_id, account_id)
            f_poisson = poisson_res["burst_factor"]

        # 2. 自动域名识别 (针对 Email 提取后缀)
        email_domain = None
        if platform == "email" and "@" in external_sender_id:
            email_domain = external_sender_id.split("@")[-1]

        # 3. 提取用户偏好因子
        pref_res = self.pref_scorer.calculate(
            account_id=account_id,
            platform=platform,
            sender_id=external_sender_id,
            current_topic=current_topic,
            email_domain=email_domain
        )
        f_pref = pref_res["preference_factor"]

        # 4. 执行非线性融合计算 (平方根平滑)
        # 公式：Final = AI_Score * sqrt(Poisson * Preference)
        raw_multiplier = f_poisson * f_pref
        smooth_multiplier = math.sqrt(raw_multiplier)

        final_score = round(ai_score * smooth_multiplier)
        # 强制约束在 1-10 分之间
        final_score = max(1, min(10, final_score))

        # ---------------------------------------------------------
        # 5. 💥 冷数据持久化：为深度学习准备“特征快照”
        # ---------------------------------------------------------
        analysis_snapshot = {
            "algorithm_version": "v1.1-sqrt-smooth",
            "ai_logic": {
                "base_score": ai_score,
                "extracted_topic": current_topic
            },
            "behavioral_features": {
                "poisson_factor": f_poisson,
                "preference_factor": f_pref,
                "combined_multiplier": round(smooth_multiplier, 4)
            },
            "metadata": {
                "sender": external_sender_id,
                "domain": email_domain
            }
        }

        new_payload = AnalysisPayload(
            notification_id=notification_id,
            account_id=account_id,
            platform=platform,
            analysis_data=analysis_snapshot,
            user_feedback_score=None  # 预留给前端用户反馈的占位符
        )
        self.db.add(new_payload)

        # ---------------------------------------------------------
        # 6. 热数据持久化：更新 Session 状态表，供前端即时排序
        # ---------------------------------------------------------
        if platform == "instagram":
            session = self.db.query(IMSessionState).filter_by(
                external_sender_id=external_sender_id,
                account_id=account_id
            ).first()
            if session:
                session.priority_score = final_score
                session.current_topic = current_topic

                # 💥 核心新增：只要有新消息被 AI 处理并更新分数，必须强制点亮该会话的红点！
                session.is_read = False

                # 注意：Session 级别的更新会被最新的消息评分覆盖，而冷表记录了每一次计算

        return {
            "final_priority": final_score,
            "analysis_snapshot": analysis_snapshot
        }