import asyncio
from openai import AsyncOpenAI


async def test_gemini_engine():
    print("🔌 正在绕过 .env，直接初始化 AI 引擎...")

    # 💥 终极测试：直接把刚复制的 Key 写死在这里！
    # 替换下面的 YOUR_KEY_HERE，务必保留双引号，不要有任何空格
    TEST_KEY = "AIzaSyC-w0oll7zNskQ-INqmt6gPdTqt6GwH_8o"

    client = AsyncOpenAI(
        api_key=TEST_KEY,
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )

    print("🚀 正在向 Google 服务器发送测试请求，请稍候...")

    try:
        response = await client.chat.completions.create(
            model="gemini-2.5-flash",  # 先用最稳的 1.5 测试
            messages=[
                {"role": "system", "content": "你是一个严格返回 JSON 的机器。"},
                {"role": "user", "content": "请输出一个测试用的 JSON，包含一个名为 'status'，值为 'success' 的字段。"}
            ],
            response_format={"type": "json_object"}
        )

        print("\n🎉 成功收到回传数据！引擎点火成功！")
        print("🤖 AI 原始输出:")
        print(response.choices[0].message.content)

    except Exception as e:
        print(f"\n❌ 引擎点火失败: {e}")


if __name__ == "__main__":
    asyncio.run(test_gemini_engine())