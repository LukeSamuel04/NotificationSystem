# app/models/__init__.py
# 把所有的 ORM 模型都在这里显式导入一遍
# 这样可以保证只要引用了 models 模块，所有的类都会被注册到 SQLAlchemy 的全局字典中
from app.models.account import FetchAccount
from app.models.notification_payloads import NotificationPayload
from app.models.account import FetchAccount
from app.models.notifications import Notification
from app.models.email_analysis import EmailAnalysis
from app.models.im_session import IMSessionState