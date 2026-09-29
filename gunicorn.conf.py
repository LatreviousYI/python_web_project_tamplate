import os
import multiprocessing

app_env = os.getenv("APP_ENV")  # None
daemon = False  # 是否以守护进程的方式启动
bind = "0.0.0.0:8779"
pidfile = "gunicorn.pid"
workers = multiprocessing.cpu_count() if app_env not in ("dev", "uat") else 2
# workers = multiprocessing.cpu_count() * 2 + 1
# workers = 1
accesslog = "./logs/gunicorn_access.log"
# 因为使用UvicornWorker 日志格式配置不生效
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
# 配置错误日志的路径
errorlog = "./logs/gunicorn_error.log"

# 可以选择日志级别，例如 'debug', 'info', 'warning', 'error', 'critical'
loglevel = "info"
worker_class = "uvicorn.workers.UvicornWorker"

wsgi_app = "factory.main:app"