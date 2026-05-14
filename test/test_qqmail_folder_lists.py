# test_list_folders.py
import asyncio
import aioimaplib

# 直接用你的配置
IMAP_SERVER = "imap.qq.com"
EMAIL_ACCOUNT = "3489130766@qq.com"
EMAIL_PASSWORD = "ckrdwvywzengdbeg"


async def probe_folders():
    print("真理探针就绪，正在连接 QQ 邮箱拉取最原始目录树...")
    try:
        client = aioimaplib.IMAP4_SSL(host=IMAP_SERVER)
        await client.wait_hello_from_server()
        await client.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)

        # 请求全量列表
        status, folder_list = await client.list('""', '"*"')

        print("\n" + "=" * 50)
        print(" 🎯 腾讯云端返回的原始字节流列表 (绝对真实) ")
        print("=" * 50)

        if status == "OK":
            for i, raw_bytes in enumerate(folder_list):
                # 打印原始字节流，看清它的真面目
                print(f"[{i + 1}] 原始 Bytes: {raw_bytes}")
                # 尝试安全解码对比
                try:
                    print(f"    安全解码: {raw_bytes.decode('utf-8', errors='replace')}")
                except Exception:
                    pass
                print("-" * 40)
        else:
            print(f"请求失败状态: {status}")

        await client.logout()
    except Exception as e:
        print(f"探测崩溃: {e}")


if __name__ == "__main__":
    asyncio.run(probe_folders())