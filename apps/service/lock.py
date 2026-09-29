"""
分布式锁业务层

基于 osc_distributed_lock 表实现（lock_key 唯一约束保证互斥）：
- 加锁 = INSERT（主键冲突即失败），成功返回自增主键 id
- 解锁 = 按 lock_key + owner 条件 DELETE
- 过期自动释放 = 加锁成功后启动后台任务，sleep ttl 后按 id 删除该锁行

DB 会话由路由通过 common.db.get_session 注入。
"""

import asyncio
import datetime
from typing import Any, Coroutine

from asyncmy import IntegrityError
from vorm import Session

from apps.model.common import DistributedLock
from common.db import get_engine, get_asynccontext_session
from utils import log_util

_TABLE = DistributedLock.table_name()

# 持有后台任务引用，避免事件循环仅持弱引用导致任务被提前回收
_background_tasks: set[asyncio.Task] = set()


def _spawn(coro: Coroutine[Any, Any, Any]) -> None:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def acquire_lock(lock_key: str, owner: str, ttl: int = 30) -> int | None:
    """尝试获取分布式锁，成功返回锁的自增主键 id，失败（已被占用）返回 None。

    靠 lock_key 唯一约束保证互斥：INSERT 成功即抢到锁，主键冲突（IntegrityError）即失败。
    """
    async with get_asynccontext_session() as session:
        lock = DistributedLock(
            lock_key=lock_key,
            owner=owner,
            expire_at=datetime.datetime.now() + datetime.timedelta(seconds=ttl),
        )
        try:
            await session.save(lock)
        except IntegrityError:
            log_util.logger.debug("分布式锁 %s 已被占用，owner=%s", lock_key, owner)
            return None
        # 抢到锁后启动后台任务：到期自动删除该锁（过期自动释放）
        _spawn(_auto_release_after(lock.id, ttl))
        return lock.id


async def _auto_release_after(lock_id: int, ttl: int) -> None:
    """后台任务：sleep 到期后删除指定 id 的锁行。

    用独立会话执行删除（请求级 session 早已关闭）；若锁已被主动释放，按 id 删除只是空操作。
    """
    await asyncio.sleep(ttl)
    async with get_asynccontext_session() as session:
        await session.execute_raw(f"DELETE FROM {_TABLE} WHERE id = %s", [lock_id])


async def release_lock(session: Session, lock_key: str, owner: str) -> bool:
    """释放锁：仅当 owner 匹配时删除，避免误删他人锁。返回是否真的释放成功。"""
    affected = await session.execute_raw(
        f"DELETE FROM {_TABLE} WHERE lock_key = %s AND owner = %s",
        [lock_key, owner],
    )
    return affected > 0


async def cleanup_expired_locks() -> int:
    """兜底清理所有已过期的锁，返回清理条数。

    后台任务覆盖正常到期释放；此函数用于进程重启等场景，清理因进程退出而遗留的过期锁。
    可在应用启动时或定时任务中调用。
    """
    engine = await get_engine()
    session = engine.session()
    return await session.execute_raw(
        f"DELETE FROM {_TABLE} WHERE expire_at < %s",
        [datetime.datetime.now()],
    )
