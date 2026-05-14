# workers/ai/models/email/scorer.py
import os
import logging
from typing import Optional
from pydantic import BaseModel, ValidationError
from openai import AsyncOpenAI
from dotenv import load_dotenv, find_dotenv

logger = logging.getLogger("EmailScorer")
load_dotenv(find_dotenv(), override=True)

ai_client = AsyncOpenAI(
    api_key=os.getenv("LLM_API_KEY"),
    base_url=os.getenv("LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
)
DEFAULT_MODEL = os.getenv("LLM_MODEL_NAME", "gemini-2.5-flash")

class EmailAIResult(BaseModel):
    category_id: int    # 💥 改为强类型的整数 ID
    priority_score: int
    summary: str


async def analyze_email_context(email_script: str) -> Optional[EmailAIResult]:
    """
    基于 7 维矩阵与动态摘要的 Email AI 核心打分引擎
    """
    system_prompt = """你是一个专门为我处理电子邮件的顶级私人 AI 助理。你的任务是阅读一段经过清洗提纯的邮件对话剧本，并提取核心状态。
    剧本中包含了【邮件主题】、【对话背景】以及【！！当前待处理邮件！！】。

    请严格按照以下要求进行评估，重点关注【当前待处理邮件】的核心诉求：

    1. 【分类 ID (category_id)】：请严格输出 1 到 7 的整数，对应以下七大分类：
       1: 紧急告警 (如：服务器宕机、异地登录、高危安全提醒)
       2: 验证码与重置 (如：登录验证码、重置密码链接)
       3: 工作与学业 (如：教授通知、作业提醒、项目沟通)
       4: 财务与物流 (如：账单、发票、快递状态、充值成功)
       5: 私人社交 (如：真人的邮件沟通、聚会邀请)
       6: 系统与订阅 (如：技术周报、GitHub PR 提醒、平台例行通知)
       7: 垃圾与推销 (如：打折广告、无营养推销)

    2. 【紧急度评分 (priority_score)】：给出一个 1-10 的整数评分：
       - 分类 2 (验证码) 且是最新的：必须给 10 分。
       - 分类 1 (紧急告警)：通常 9-10 分。
       - 分类 7 (垃圾推销)：必须强制为 1 分。
       - 其他分类根据诉求的时效性和重要性在 2-8 分之间评估。
       - ⚠️ 注意：如果剧本最后一条显示是我自己发出的（或者表明我已经妥善处理了），说明正在“等待对方回复”，无论什么分类，紧急度应强制降至 1-3 分。

    3. 【智能摘要 (summary)】：根据分类动态决定摘要的长度和格式：
       - 如果是分类 2 (验证码)：直接输出“验证码：XXXX”或提取核心链接，绝对不要加废话。
       - 如果是分类 7 (垃圾推销)：极简概括，例如“Willys 的促销广告”。
       - 其他分类：用 1-2 句话精炼总结核心诉求和接下来的行动指令（例如“AWS发来服务器报价，需周五前回复”）。

    必须直接返回纯洁的 JSON 字符串，且严格包含以下字段：
    {
        "category_id": int,
        "priority_score": int,
        "summary": "string"
    }
    【极其重要】：绝对不要使用 ```json 等代码块标记包裹数据！也不要包含任何类似“Here is the JSON”的提示性废话！只输出大括号 {} 及其内部的内容！
    """

    try:
        logger.debug(f"🧠 准备向 {DEFAULT_MODEL} 发送邮件剧本，长度: {len(email_script)}")

        response = await ai_client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"以下是邮件剧本：\n\n{email_script}"}
            ],
            temperature=0.0,  # 💥 温度降到最低 0，保证分类 ID 绝对稳定，杜绝幻觉
            max_tokens=2000
        )

        raw_json_str = response.choices[0].message.content

        if not raw_json_str:
            logger.error("❌ AI 返回了空值。")
            return None

        logger.debug(f"🤖 AI 原始返回: {raw_json_str}")

        start_idx = raw_json_str.find('{')
        end_idx = raw_json_str.rfind('}')

        if start_idx != -1 and end_idx != -1 and start_idx < end_idx:
            clean_json_str = raw_json_str[start_idx:end_idx + 1]
        else:
            clean_json_str = raw_json_str

        # 验证 JSON 并转换为对象
        result = EmailAIResult.model_validate_json(clean_json_str)
        return result

    except ValidationError as ve:
        logger.error(f"❌ 数据不符合 Schema: {ve}\n脏数据: {raw_json_str}")
        return None
    except Exception as e:
        logger.error(f"💥 AI 接口严重错误: {e}")
        return None