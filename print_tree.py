import os


def generate_tree(dir_path, prefix=""):
    # 过滤掉 AI 不需要看的配置和依赖文件夹
    ignore_dirs = {'.git', 'node_modules', 'venv', '.venv', '__pycache__', '.idea', 'build', 'dist'}

    try:
        items = os.listdir(dir_path)
    except PermissionError:
        return

    items = [f for f in items if not f.startswith('.')]
    items.sort()

    for i, item in enumerate(items):
        path = os.path.join(dir_path, item)
        is_last = i == (len(items) - 1)
        connector = "└── " if is_last else "├── "

        if os.path.isdir(path):
            if item not in ignore_dirs:
                print(prefix + connector + item + "/")
                extension = "    " if is_last else "│   "
                generate_tree(path, prefix + extension)
        else:
            print(prefix + connector + item)


if __name__ == "__main__":
    print("Notification System Project/")
    generate_tree(".")