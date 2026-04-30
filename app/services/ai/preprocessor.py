import re

def clean_email_text(subject: str, content: str) -> str:
    """
    Email cleaning function: 负责将生肉文本清洗为纯净字符串
    """
    # 1. Combine the topic with the content.
    raw_text = f"{subject} {content}"

    # 2. Delete html labels.
    clean_text = re.sub(r'<.*?>', '', raw_text)

    # 3. Whitespace normalization.
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()

    # 4. Return preprocessed data.
    return clean_text