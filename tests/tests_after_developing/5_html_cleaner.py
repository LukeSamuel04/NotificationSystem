# tests/tests_after_developing/5_html_cleaner.py
import unittest
import sys
import os

# 确保项目根目录在 PYTHONPATH 中，防止 IDE 单点运行时报导入错误
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入待测的 HTML 清洗器函数
from workers.notification.utils.html_cleaner import clean_html


class TestHtmlCleaner(unittest.TestCase):

    def test_clean_empty_and_none(self):
        """【测试 1】边界输入：验证当输入为空值或 None 时，优雅返回空字符串而不会引发崩溃"""
        self.assertEqual(clean_html(""), "")
        self.assertEqual(clean_html(None), "")

    def test_decompose_non_content_tags(self):
        """【测试 2】干扰标签剥离：验证 <script>、<style>、<meta> 等非内容标签是否被彻底物理粉碎 (decompose)"""
        dirty_html = """
        <html>
            <head>
                <title>系统通知</title>
                <meta charset="UTF-8">
                <style>body { background: #fff; }</style>
                <script>console.log("XSS Tracker Token");</script>
            </head>
            <body>
                <p>这是真正的正文内容</p>
                <noscript>请开启 JavaScript</noscript>
            </body>
        </html>
        """
        result = clean_html(dirty_html)

        # 断言判定：正文必须留下来，而那些高危和排版标签里的文字必须被死死卡住，完全蒸发
        self.assertIn("这是真正的正文内容", result)
        self.assertNotIn("XSS Tracker Token", result)
        self.assertNotIn("body {", result)
        self.assertNotIn("系统通知", result)
        self.assertNotIn("请开启 JavaScript", result)

    def test_decompose_hidden_elements(self):
        """【测试 3】隐藏元素过滤：验证包含 display:none、visibility:hidden 等垃圾像素或广告追踪器是否被完美剥离"""
        hidden_html = """
        <div>
            <h1>合法可见正文</h1>
            <div style="display: none;">我是隐藏的垃圾推广文本</div>
            <span style="visibility: hidden ; font-size: 12px;">广告追踪像素</span>
            <p style="MAX-HEIGHT: 0px; overflow: hidden;">旧版排版干扰文本</p>
        </div>
        """
        result = clean_html(hidden_html)

        # 断言判定：合法的正文完整保留，但所有隐藏元素的文本内容应该全盘抹除
        self.assertIn("合法可见正文", result)
        self.assertNotIn("我是隐藏的垃圾推广文本", result)
        self.assertNotIn("广告追踪像素", result)
        self.assertNotIn("旧版排版干扰文本", result)

    def test_markdown_conversion(self):
        """【测试 4】Markdown 平铺转换：验证基础的 HTML 标签能被正确转译为可读性强的纯文本格式"""
        html_markup = """
        <div>
            <h2>邮件重要通知</h2>
            <p>请LukeSamuel同学注意，你的<strong>PA2552自动化测试</strong>分支已通过审核。</p>
        </div>
        """
        result = clean_html(html_markup)

        # 断言判定：强标签转换出的文字结构干净，且多余的包裹标记被 html2text 提纯
        self.assertIn("邮件重要通知", result)
        self.assertIn("请LukeSamuel同学注意", result)
        self.assertIn("PA2552自动化测试", result)

    def test_whitespace_and_newline_compression(self):
        """【测试 5】空白符与无休止换行压缩：验证特种零宽空白字符被替换，以及连续超过3个的野蛮换行被强行压实"""
        # 构造带有零宽空白符(\u200B)和一堆连续回车的极端报文
        whitespace_html = (
            "<p>Luke\u200BCode</p>"
            "<br><br><br><br><br>"
            "<p>Second Paragraph</p>"
        )
        result = clean_html(whitespace_html)

        # 1. 验证特种零宽字符被替换为空格，从而文本能被正常断字匹配
        self.assertIn("Luke Code", result)

        # 2. 验证多重连续换行有没有被 re.sub 压缩为标准的双换行段落分隔（\n\n）
        # 如果压缩成功，结果中绝对不应该存在连续 3 个以上的 \n
        self.assertNotIn("\n\n\n", result)
        self.assertIn("\n\n", result)


# 💥 挂载标准单元测试启动入口，在 IDE 中允许直接一键点击点击运行
if __name__ == "__main__":
    unittest.main()