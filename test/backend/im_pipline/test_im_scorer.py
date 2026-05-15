# test/test_im_scorer.py
import asyncio
import sys
import os

# 将项目根目录加入路径，确保能导入 app 和 workers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.ai.models.social_media.scorer import analyze_social_media_session

# --- 虚构的测试数据上下文 ---

# 场景 1: 日常闲聊（低优先级）
CONTEXT_DAILY_CHAT = """
[2026-05-08 10:00] 对方: 哈哈，你看到那个猫片了吗？太逗了。
[2026-05-08 10:05] 对方: [视频附件]
"""

# 场景 2: 明确的任务请求 + 询问（中高优先级）
CONTEXT_TASK_REQUEST = """
[2026-05-08 11:00] 对方: 那个...你上次说的那个 FastAPI 的跨域配置，能发我一份代码参考吗？
[2026-05-08 11:02] 对方: 我这边一直报 403 错误，急着上线，求救求救！
"""

# 场景 3: 多话题混杂（复杂场景：技术求助 + 约饭）
CONTEXT_MULTI_TOPIC = """
[2026-05-08 14:00] 对方: 兄弟，今天晚上 Karlskrona 那家火锅去不去？
[2026-05-08 14:01] 对方: 另外，我 3D 打印机的切片设置好像有点问题，底层粘不住，你帮我看看参数？
"""

# 场景 4: 我已经回复过了（优先级应自动降低）
CONTEXT_ALREADY_REPLIED = """
[2026-05-08 15:00] 对方: 你什么时候有空帮我修一下电脑？
[2026-05-08 15:10] 我: 晚上八点以后吧，我现在的课还没上完。
"""


async def run_test():
    test_cases = [
        ("日常闲聊", CONTEXT_DAILY_CHAT),
        ("技术求救", CONTEXT_TASK_REQUEST),
        ("多话题场景", CONTEXT_MULTI_TOPIC),
        ("已回复场景", CONTEXT_ALREADY_REPLIED),
    ]

    print("🧪 开始 IM Scorer 单元测试 (Gemini Flash)...\n")
    print("-" * 60)

    for name, context in test_cases:
        print(f"📡 测试用例: 【{name}】")
        print(f"📝 模拟剧本内容:\n{context.strip()}")

        result = await analyze_social_media_session(context)

        if result:
            print(f"✅ AI 响应成功:")
            print(f"   🔹 提取话题: {result.current_topic}")
            print(f"   🔹 紧急评分: {result.priority_score}/10")
            print(f"   🔹 浓缩摘要: {result.summary_snapshot}")
        else:
            print(f"❌ AI 响应失败或解析错误。")

        print("-" * 60)


if __name__ == "__main__":
    # 确保你的 .env 文件在根目录
    asyncio.run(run_test())