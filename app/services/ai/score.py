# app/services/ai/score.py
from transformers import pipeline
import os

# 阻止一些不必要的警告信息
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# ==========================================
# 业务超参数配置 (Hyperparameters)
# ==========================================
AI_ALPHA = 0.6  # 分数计算公式中，业务权重的占比 (0~1 之间)

# 分类标签及其对应的业务权重配置
CATEGORY_WEIGHTS = {
    "urgent_alert": 0.9,
    "study_work": 0.8,
    "bills_housing": 0.7,
    "social_personal": 0.4,
    "advertisement_spam": 0.1
}

print("--- [系统提示] 正在初始化本地 AI 模型... ---")
print("--- [系统提示] 首次启动将下载约 260MB 模型文件，请保持网络畅通 ---")

try:
    # 加载零样本分类流水线
    classifier = pipeline(
        "zero-shot-classification",
        model="typeform/distilbert-base-uncased-mnli",
        device=-1  # 强制使用 CPU 运行
    )
    print("--- [系统提示] 本地 AI 模型加载成功！ ---")
except Exception as e:
    print(f"--- [警告] 本地模型加载失败: {e} ---")
    classifier = None


def analyze_email_priority(subject: str, content: str) -> dict:
    """
    完全在本地 CPU 运行的邮件优先级分析逻辑
    :param subject: 邮件/通知的标题
    :param content: 邮件/通知的洗净后的正文
    :return: 包含分数、分类和摘要(为 None)的字典
    """
    # 如果模型加载失败，返回容错的字典数据
    if classifier is None:
        print("--- [错误] 模型未加载，返回保底分 ---")
        return {"priority_score": 5.0, "category": "local_error", "summary": None}

    # 1. 容错处理：确保即使传入全空字符串也能正常运转
    safe_subject = subject.strip() if subject.strip() else "No Subject"
    safe_content = content.strip() if content.strip() else "No Content"

    # 如果标题和内容全是空的，直接打入垃圾箱
    if safe_subject == "No Subject" and safe_content == "No Content":
        return {"priority_score": 2.0, "category": "advertisement_spam", "summary": None}

    # 2. 内部拼装给模型“吃”的文本
    text_to_analyze = f"Subject: {safe_subject}. Content: {safe_content}"

    # 动态获取标签列表
    labels = list(CATEGORY_WEIGHTS.keys())

    try:
        # 3. 本地推理
        result = classifier(text_to_analyze, candidate_labels=labels)

        # 解析结果
        category = result['labels'][0]
        confidence = result['scores'][0]

        # 4. 计算得分
        w_cat = CATEGORY_WEIGHTS.get(category, 0.5)
        raw_score = (AI_ALPHA * w_cat + (1 - AI_ALPHA) * confidence) * 10
        final_score = round(min(max(raw_score, 0.0), 10.0), 2)

        print(f"--- [本地 AI 分析成功] 分类: {category}, 最终分: {final_score} ---")

        # 5. 返回字典（对齐 manager 的期待格式）
        return {
            "priority_score": final_score,
            "category": category,
            "summary": None  # 本地分类模型不负责生成摘要，安全置空
        }

    except Exception as e:
        print(f"--- [异常] 推理过程出错: {e} ---")
        return {"priority_score": 5.0, "category": "general", "summary": None}