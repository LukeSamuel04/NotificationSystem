#循环检查待处理数据库，将所有待处理数据都给ai评分
import sys
import os
import time
from dotenv import load_dotenv

# ==========================================
# 1. 环境初始化 (和 manager.py 完全一样)
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

# ==========================================
# 2. 导入数据库和核心 Service
# ==========================================
from app.db.session import SessionLocal
from app.services.ai.score_manager import process_pending_notifications


def run_ai_worker():
    """
    AI 消费端守护进程 (Daemon)
    """
    print("🤖 AI 质检中心启动！开始全天候轮询生肉数据...")

    # 建立一个永不停止的死循环（这正是 Worker 的特征）
    while True:
        # 每次循环申请一辆数据库连接车
        db = SessionLocal()
        try:
            # 【核心召唤】：呼叫大脑进行算分
            processed_count = process_pending_notifications(db, batch_size=50)

            if processed_count == 0:
                # 策略 A：如果没活干，就睡 10 秒，防止把 CPU 占满和疯狂骚扰 MySQL
                time.sleep(10)
            else:
                # 策略 B：如果刚才处理了一大批数据，说明可能还有积压，休息 2 秒立刻继续干
                time.sleep(2)

        except KeyboardInterrupt:
            print("\n🛑 收到退出指令，AI Worker 安全关闭。")
            break
        except Exception as e:
            print(f"🔥 Worker 遇到致命错误: {e}")
            time.sleep(10)  # 如果遇到网络波动或数据库闪断，睡 10 秒后自动重试
        finally:
            # 无论如何，必须释放连接车
            db.close()


if __name__ == "__main__":
    run_ai_worker()