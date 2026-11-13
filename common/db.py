"""
数据库引擎与会话管理

基于 vorm 的 MySQL 引擎，惰性创建并复用连接池。
连接池由 factory/bootstrap.py 在应用启动阶段创建。
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Protocol, cast

from vorm import create_mysql_engine

from configs import settings
from utils import cipher_util

mysql_engine = None
engine_lock = asyncio.Lock()


class DbSettings(Protocol):
    """类型约束，实际数据库配置只定义在各环境配置类中。"""

    db_host: str
    db_port: int
    db_user: str
    db_pass: str
    db_name: str
    db_pool_min_size: int
    db_pool_max_size: int


db_settings = cast(DbSettings, settings)


def validate_db_settings() -> None:
    """在创建连接池前检查必要配置，避免不透明的属性或解密错误。"""
    required_settings = ("db_host", "db_user", "db_pass", "db_name")
    missing = [name for name in required_settings if not getattr(settings, name)]
    if missing:
        raise RuntimeError(f"数据库配置缺失: {', '.join(missing)}")


async def get_engine():
    """惰性创建并返回全局 MySQL 引擎（连接池复用）。"""
    global mysql_engine
    if mysql_engine is None:
        async with engine_lock:
            if mysql_engine is None:
                validate_db_settings()
                mysql_engine = await create_mysql_engine(
                    host=db_settings.db_host,
                    port=db_settings.db_port,
                    user=db_settings.db_user,
                    password=cipher_util.cipher.decrypt(db_settings.db_pass),
                    database=db_settings.db_name,
                    minsize=db_settings.db_pool_min_size,
                    maxsize=db_settings.db_pool_max_size,
                    autocommit=True,
                )
    return mysql_engine


async def close_engine() -> None:
    """关闭连接池并清除全局引用，允许同一进程再次初始化。"""
    global mysql_engine
    async with engine_lock:
        if mysql_engine is not None:
            await mysql_engine.close()
            mysql_engine = None


async def get_session():
    """FastAPI 依赖：提供一个 vorm Session（请求结束自动关闭）。"""
    engine = await get_engine()
    session = engine.session()
    try:
        yield session
    finally:
        await session.close()


@asynccontextmanager
async def get_asynccontext_session():
    """提供一个 vorm Session（自动关闭）。"""
    engine = await get_engine()
    session = engine.session()
    try:
        yield session
    finally:
        await session.close()
