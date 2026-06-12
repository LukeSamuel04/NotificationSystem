import os
import sys
import subprocess
import time


def main():
    # 1. 定位测试文件夹路径
    project_root = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.join(project_root, 'tests', 'tests_after_developing')

    if not os.path.exists(test_dir):
        print(f"❌ 找不到测试目录: {test_dir}")
        return

    files = [f for f in os.listdir(test_dir) if f.endswith('.py') and f != '__init__.py']

    # 2. 核心逻辑：按文件名前缀数字进行精确排序
    def get_prefix_num(filename):
        try:
            return int(filename.split('_')[0])
        except ValueError:
            return 999

    test_files = sorted(files, key=get_prefix_num)

    print("==================================================")
    print(f"🚀 核心测试引擎启动 | 共发现 {len(test_files)} 个独立测试模块")
    print("==================================================\n")

    passed_tests = []
    failed_tests = []
    start_time = time.time()

    # 3. 隔离环境逐一执行测试
    for index, filename in enumerate(test_files, 1):
        file_path = os.path.join(test_dir, filename)
        print(f"▶️ [{index}/{len(test_files)}] 正在执行: {filename} ...")

        try:
            # 💥 核心修复：强行指定 encoding='utf-8'，并使用 capture_output=True 捕获
            result = subprocess.run(
                [sys.executable, "-m", "unittest", file_path],
                capture_output=True,
                text=True,
                encoding='utf-8',  # 解决 Windows GBK 导致读取 Emoji 崩溃的问题
                errors='replace'  # 遇到极端乱码直接替换，绝不崩溃
            )

            if result.returncode == 0:
                print(f"   ✅ 通过\n")
                passed_tests.append(filename)
            else:
                print(f"   ❌ 失败")
                print("   --- 错误日志片段 ---")

                # 💥 容错修复：防止 stderr 为空导致 NoneType 崩溃
                err_content = result.stderr if result.stderr else result.stdout
                if err_content:
                    error_output = err_content.strip().split('\n')[-15:]  # 多截取几行方便看报错
                    print("   " + "\n   ".join(error_output))
                else:
                    print("   (无控制台输出)")

                print("   --------------------\n")
                failed_tests.append(filename)

        except Exception as e:
            # 万一底层崩溃，捕获异常，保证下一个测试继续跑
            print(f"   ❌ 驱动器捕获到进程异常: {e}\n")
            failed_tests.append(filename)

    # 4. 打印最终答辩级测试报告
    total_time = time.time() - start_time
    print("==================================================")
    print("📊 自动化测试矩阵执行报告")
    print("==================================================")
    print(f"⏱️  总耗时: {total_time:.2f} 秒")
    print(f"✅  通过模块: {len(passed_tests)} 个")
    print(f"❌  失败模块: {len(failed_tests)} 个")

    if failed_tests:
        print("\n⚠️ 存在未通过的测试模块:")
        for ft in failed_tests:
            print(f"   - {ft}")
        sys.exit(1)
    else:
        print("\n🎉 完美！所有 23 个测试模块均以 100% 绿灯通过！系统坚如磐石！")
        sys.exit(0)


if __name__ == "__main__":
    main()