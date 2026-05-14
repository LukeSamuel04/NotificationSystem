# app/services/local_scoring/poission_urgency_scorer/im/scorer.py
import math
from datetime import datetime, timedelta
from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

# 引入底层ORM模型 (根据你实际的项目路径按需微调引入方式)
from app.models.notifications import Notification
from app.models.im_session import IMSessionState


class IMPoissonUrgencyScorer:
    """
    IM 场景下的基于动态滑动窗口的泊松分布紧急度算子。
    【已净化】：彻底剥离隐式建档越权行为，回归纯粹的数学精算与安全状态只读/更新职责。
    """

    def __init__(self, db: Session):
        self.db = db
        # 核心业务阈值配置
        self.COLD_START_THRESHOLD = 20      # 跨越冷启动所需的历史最小样本数
        self.BURST_WINDOW_MINUTES = 30      # 滑动监测窗口大小 (30分钟)
        self.DEFAULT_LAMBDA_FLOOR = 2.0     # 30分钟窗口的兜底期望值下限，防止过度敏感

    def calculate(self, external_sender_id: str, account_id: str) -> Dict[str, Any]:
        """
        执行突发特征提取，并仅在窗口档案已存在时顺路维护历史基线 historical_lambda。
        输出标准契约: is_burst_active, poisson_probability, burst_factor
        """
        now = datetime.now()

        # ---------------------------------------------------------------------
        # 步骤一：全量样本核算与存活周期提取 (顺风车数据准备)
        # ---------------------------------------------------------------------
        # 获取该联系人的历史总发信量及第一条消息的时间戳
        stats = self.db.query(
            func.count(Notification.id).label("total_msgs"),
            func.min(Notification.received_at).label("first_msg_at")
        ).filter(
            Notification.external_sender_id == external_sender_id,
            Notification.account_id == account_id
        ).first()

        total_msgs = stats.total_msgs if stats and stats.total_msgs else 0
        first_msg_at = stats.first_msg_at if stats and stats.first_msg_at else now

        # ---------------------------------------------------------------------
        # 步骤二：冷启动防线拦截
        # ---------------------------------------------------------------------
        if total_msgs < self.COLD_START_THRESHOLD:
            return {
                "is_burst_active": False,
                "poisson_probability": 1.0,
                "burst_factor": 1.0
            }

        # ---------------------------------------------------------------------
        # 步骤三：惰性顺风车更新长期基线 historical_lambda
        # ---------------------------------------------------------------------
        # 计算账号存活总小时数 (设立极小保底值规避除零错误)
        survival_seconds = (now - first_msg_at).total_seconds()
        survival_hours = max(survival_seconds / 3600.0, 0.1)

        # 真实长期每小时平均发信量
        real_hourly_lambda = total_msgs / survival_hours

        # 实时查询 Session 状态表中的档案是否存在
        session_state = self.db.query(IMSessionState).filter_by(
            external_sender_id=external_sender_id,
            account_id=account_id
        ).first()

        # 💥 核心重构：绝对剥离越权建档 (db.add) 的副作用！
        # 只有当执行器/网关层前置显式开辟了该窗口档案时，算子才顺道执行纯粹的参数刷新。
        if session_state:
            session_state.historical_lambda = float(real_hourly_lambda)
            # 依靠调用方统一 commit，保持事务干净

        # ---------------------------------------------------------------------
        # 步骤四：滑动窗口实时捕获当前观测密度 (k)
        # ---------------------------------------------------------------------
        window_start = now - timedelta(minutes=self.BURST_WINDOW_MINUTES)
        k = self.db.query(Notification).filter(
            Notification.external_sender_id == external_sender_id,
            Notification.account_id == account_id,
            Notification.received_at >= window_start
        ).count()

        # ---------------------------------------------------------------------
        # 步骤五：严谨的数学推算 (泊松 CDF 累积概率)
        # ---------------------------------------------------------------------
        # 将小时级基线折算为当前 30 分钟窗口的数学期望值 (lambda_30)
        # 引入保底下限防线，避免长期极其安静的人发2条消息就判定为小概率轰炸
        expected_lambda_30 = max(real_hourly_lambda / 2.0, self.DEFAULT_LAMBDA_FLOOR)

        # 计算累积概率 P(X >= k)
        # P(X >= k) = 1 - sum_{i=0}^{k-1} (lambda^i * exp(-lambda)) / i!
        if k == 0:
            prob_burst = 1.0
        else:
            cdf_sum = 0.0
            # 为防止阶梯数过大导致溢出，限制安全计算范围
            safe_k = min(k, 100)
            for i in range(safe_k):
                # 利用对数域计算规避大数溢出: lambda^i * exp(-lambda) / i!
                try:
                    term = math.exp(i * math.log(expected_lambda_30) - expected_lambda_30 - math.lgamma(i + 1))
                    cdf_sum += term
                except OverflowError:
                    pass
            prob_burst = max(0.0, 1.0 - cdf_sum)

        # ---------------------------------------------------------------------
        # 步骤六：映射平滑特征因子 (Burst Factor)
        # ---------------------------------------------------------------------
        # 设定触发增益的数学边界值为 0.05 (典型统计学显著性水平)
        burst_factor = 1.0
        if prob_burst < 0.05:
            # 概率越小，因子越激进。缩放倍率设定为 20.0，使极端轰炸最高可获得 2.0 倍直接提权
            burst_factor = 1.0 + (0.05 - prob_burst) * 20.0
            burst_factor = min(round(burst_factor, 2), 2.0)  # 封顶 2.0 倍因子

        return {
            "is_burst_active": True,
            "poisson_probability": round(prob_burst, 5),
            "burst_factor": burst_factor
        }