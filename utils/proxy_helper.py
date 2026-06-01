# app/utils/proxy_helper.py
import os
import logging

logger = logging.getLogger("ProxyHelper")


def inject_local_proxy(proxy_url: str = "http://127.0.0.1:7897"):
    """
    模块化的代理注入函数。
    在需要突破网络限制的文件顶部调用此函数，即可让当前运行上下文走指定代理。
    同时自动配置局域网白名单 (NO_PROXY)，防止误杀本地服务如 FastAPI 和数据库。

    :param proxy_url: 你的本地代理地址，默认使用 Clash Mihomo 的 7897 端口
    """
    # 注入全局代理
    os.environ["HTTP_PROXY"] = proxy_url
    os.environ["HTTPS_PROXY"] = proxy_url
    os.environ["http_proxy"] = proxy_url
    os.environ["https_proxy"] = proxy_url

    # 注入局域网直连白名单 (极其重要，防止前端 500)
    os.environ["NO_PROXY"] = "localhost, 127.0.0.1, ::1"
    os.environ["no_proxy"] = "localhost, 127.0.0.1, ::1"

    logger.debug(f"🔌 局部网络代理已就绪: {proxy_url} (已放行本地流量)")