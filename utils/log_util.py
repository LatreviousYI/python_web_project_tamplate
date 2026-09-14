"""
日志工具模块

提供统一的日志配置和日志记录功能，使用 nb_log 库实现
"""

import logging
import sys

from configs import settings

# 创建日志目录
log_dir = settings.basedir.joinpath(f"logs/{settings.app_name}")
log_dir.mkdir(parents=True, exist_ok=True)

# 将项目路径插入到sys.path[1]的位置,这样nb_log就能读取当前项目下的nb_log_config.py文件
sys.path.insert(1, str(settings.basedir))
from nb_log import get_logger

# 配置各模块日志
# https://nb-log-doc.readthedocs.io/zh-cn/latest/articles/c1.html#
get_logger(name="uvicorn.access", log_filename="uvicorn_access.log")

# 主应用日志记录器
logger = get_logger(name="osc", log_filename="osc.log")

# 开发环境下降低第三方库的日志级别，避免日志噪音
if settings.env == "dev":
    get_logger(name="apscheduler.scheduler", log_level_int=logging.ERROR)
    get_logger(name="httpx", log_level_int=logging.ERROR)
