from transformers import pipeline
import torch
import os
from app.core.config import settings

# 阻止一些不必要的警告信息
os.environ["TOKENIZERS_PARALLELISM"] = "false"

print("--- [系统提示] 正在初始化本地 AI 模型... ---")
print("--- [系统提示] 首次启动将下载约 260MB 模型文件，请保持网络畅通 ---")

try:
    # 加载零样本分类流水线
    # 模型：distilbert-base-uncased-mnli
    classifier = pipeline(
        "zero-shot-classification",
        model="typeform/distilbert-base-uncased-mnli",
        device=-1  # 强制使用 CPU 运行
    )
    print("--- [系统提示] 本地 AI 模型加载成功！ ---")
except Exception as e:
    print(f"--- [警告] 本地模型加载失败: {e} ---")
    classifier = None


def analyze_email_priority(subject: str, content: str):
    """
    完全在本地 CPU 运行的邮件优先级分析逻辑
    """
    if classifier is None:
        print("--- [错误] 模型未加载，返回保底分 ---")
        return 5.0, "local_error"

    # 1. 准备待分析文本和分类标签
    text = f"Subject: {subject}. Content: {content}"
    # 更加精准的分类体系
    labels = [
        "urgent_alert",
        "study_work",
        "bills_housing",
        "social_personal",
        "advertisement_spam"
    ]

    try:
        # 2. 本地推理
        result = classifier(text, candidate_labels=labels)

        # 解析结果：labels 里的第一个就是分数最高的类别
        category = result['labels'][0]
        confidence = result['scores'][0]

        # 3. 匹配权重（从config.py 里读取 W_XXX）
        weight_key = f"W_{category.upper()}"
        w_cat = getattr(settings, weight_key, 0.5)

        # 4. 执行优先级公式
        alpha = settings.AI_ALPHA
        raw_score = (alpha * w_cat + (1 - alpha) * confidence) * 10

        # 确保分值范围在 0-10
        final_score = round(min(max(raw_score, 0.0), 10.0), 2)

        print(f"--- [本地 AI 分析成功] 分类: {category}, 最终分: {final_score} ---")
        return final_score, category

    except Exception as e:
        print(f"--- [异常] 推理过程出错: {e} ---")
        return 5.0, "general"