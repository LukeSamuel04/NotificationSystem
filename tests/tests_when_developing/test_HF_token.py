import requests
import json

# 用最稳的小模型测试
url = "https://api-inference.huggingface.co/models/typeform/distilbert-base-uncased-mnli"
token = "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"  # 你的Token

headers = {"Authorization": f"Bearer {token}"}
payload = {
    "inputs": "I am so happy today",
    "parameters": {"candidate_labels": ["positive", "negative"]}
}

print("--- 开始测试请求 ---")
try:
    # 强制不使用系统代理，防止干扰
    response = requests.post(url, headers=headers, json=payload, timeout=20, proxies={"http": None, "https": None})

    print(f"状态码: {response.status_code}")
    print(f"返回内容: {response.text}")

    if response.status_code == 200:
        print("\n✅ 成功了！AI 能够正常工作！")
    else:
        print(response.status_code)
        print("\n❌ 依然失败，请看上面的返回内容。")

except Exception as e:
    print(f"🚨 连请求都没发出去: {e}")