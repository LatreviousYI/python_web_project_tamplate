"""
数据库引擎与会话管理

基于 vorm 的 MySQL 引擎，惰性创建并复用连接池。
当前阶段「先不连库」：引擎仅定义、不实际创建；
接库后在 factory/main.py 的 lifespan 中调用 get_engine() 并 sync_table() 建表。
"""

from vorm import create_mysql_engine

from configs import settings
from utils import cipher_util

mysql_engine = None


async def get_engine():
    """惰性创建并返回全局 MySQL 引擎（连接池复用）。"""
    global mysql_engine
    if mysql_engine is None:
        mysql_engine = await create_mysql_engine(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=cipher_util.cipher.decrypt(settings.db_pass),
            database=settings.db_name,
            minsize=10,
            maxsize=20,
            autocommit=True,
        )
    return mysql_engine


async def get_session():
    """FastAPI 依赖：提供一个 vorm Session（请求结束自动关闭）。"""
    engine = await get_engine()
    session = engine.session()
    try:
        yield session
    finally:
        await session.close()
