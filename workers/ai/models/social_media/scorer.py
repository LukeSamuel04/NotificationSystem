# workers/ai/models/social_media/scorer.py
import os
import logging
from typing import Optional
from pydantic import ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv, find_dotenv
from app.schemas.im_session import IMSessionAIResult

logger = logging.getLogger("IMScorer")
load_dotenv(find_dotenv(), override=True)

ai_client = AsyncOpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
)
DEFAULT_MODEL = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")


async def analyze_social_media_session(chat_context_script: str) -> Optional[IMSessionAIResult]:
    system_prompt = """你是一个专门为我服务的私人社交助理。你的任务是阅读一段我与联系人（朋友、家人或熟人）的即时通讯(IM)聊天记录剧本，并提取核心状态。
    剧本中包含了时间线、对方发送的消息、以及我回复的消息。

    请严格按照以下要求进行评估：
    1. 【提取话题】：用简短的词组概括对方的核心诉求。如果对话中包含多个完全不同的话题，请提取 1-3 个最核心的，并使用 " | " 分隔（例如：“周末聚餐预订 | 询问报错解决”）。请将最紧急、最需要处理的话题放在最前面。如果只是漫无目的的闲聊，请写“日常闲聊”。
    2. 【紧急度评分】：给出一个 1-10 的整数评分，衡量我需要回复对方的紧迫程度。
       - 1-3分：发表情包、分享日常/段子、对话已经自然结束。
       - 4-6分：一般的疑问、寒暄近况、不紧急的日程安排讨论。
       - 7-8分：当天马上就要发生的邀约、对方遇到困难需要建议或情感支持、重要的私人事务。
       - 9-10分：突发紧急事件、极其迫切的求助、家人朋友的急事。
       注意：如果剧本中最后一条消息是“我”发送的，说明我已经给出了回应，目前是“等待对方回复”的状态，此时该会话的紧急度应强制降至 1-3 分。
    3. 【浓缩摘要】：用 1-2 句话总结这段对话目前的进展。重点说明对方想要什么，或者我接下来是否需要采取行动。

    必须直接返回纯洁的 JSON 字符串，且严格包含以下字段：
    {
        "current_topic": "string",
        "priority_score": int,
        "summary_snapshot": "string"
    }
    【极其重要】：绝对不要使用 ```json 等代码块标记包裹数据！也不要包含任何类似“Here is the JSON”的提示性废话！只输出大括号 {} 及其内部的内容！
    """

    try:
        logger.debug(f"🧠 准备向 {DEFAULT_MODEL} 发送剧本，长度: {len(chat_context_script)}")

        response = await ai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下是聊天剧本：\n\n{chat_context_script}"}
            ],
            # 💥 核心修改 1：关掉兼容性极差的 json_object 模式
            temperature=0.1,
            # 💥 核心修改 2：给足空间，防止由于 token 限制只吐出一半
            max_tokens=3000
        )

        raw_json_str = response.choices[0].message.content

        # 💥 核心修改 3：拦截网关抽风返回空值的致命错误
        if not raw_json_str:
            logger.error("❌ AI 返回了空值 (可能触发了安全策略或网关截断)。")
            return None

        logger.debug(f"🤖 AI 原始返回: {raw_json_str}")

        start_idx = raw_json_str.find('{')
        end_idx = raw_json_str.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            clean_json_str = raw_json_str[start_idx:end_idx + 1]
        else:
            clean_json_str = raw_json_str

        result = IMSessionAIResult.model_validate_json(clean_json_str)
        return result

    except ValidationError as ve:
        logger.error(f"❌ 数据不符合 Schema: {ve}\n脏数据: {raw_json_str}")
        return None
    except Exception as e:
        logger.error(f"💥 AI 接口严重错误: {e}")
        return None