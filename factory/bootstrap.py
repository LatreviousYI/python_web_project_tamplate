"""
应用启动引导入口（bootstrap）

集中管理应用生命周期内的所有启动/关闭逻辑，factory/main.py 的 lifespan
只负责调用 startup() / shutdown()。后续新增任务统一在本文件对应区块注册，
不再改动 factory/main.py：

1. 数据库连接池创建 + 表结构同步
2. 定时任务（apscheduler）
3. 持久后台任务（forever loop）

多 worker 注意（gunicorn + UvicornWorker，见 gunicorn.conf.py）：
每个 worker 进程都会完整执行一遍 startup()，进程间内存不共享：
- 定时任务/持久任务中"只应执行一次"的逻辑，必须先抢分布式锁再执行；
- 禁止依赖进程内锁或模块级变量做跨 worker 互斥。
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from common import db
from common.db import get_engine
from utils import httpx_utils, log_util
from utils.async_task import shutdown_forever_task

scheduler: AsyncIOScheduler | None = None


# ---------- 1. 数据库 ----------


async def init_db() -> None:
    """创建数据库连接池（惰性单例，见 common/db.py）。"""
    await get_engine()
    # 同步表结构（只增改不删），新模型在此追加：
    # from apps.model.auth import User
    # async with get_asynccontext_session() as session:
    #     await User.sync_table(session.dialect)


# ---------- 2. 定时任务 ----------


def register_schedulers() -> None:
    """注册定时任务（apscheduler）。

    多 worker 下每个进程都会启动 scheduler 并触发任务，
    任务函数内部必须先抢分布式锁，抢到才真正执行。
    """
    global scheduler
    scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

    # 示例：每天 01:00 执行
    # from apps.tasks import demo
    # scheduler.add_job(demo.demo_job, "cron", hour=1, minute=0, id="demo_job", replace_existing=True)

    scheduler.start()
    log_util.logger.info("定时任务注册完成")


# ---------- 3. 持久任务 ----------


def register_forever_tasks() -> None:
    """注册常驻后台任务（asyncio 循环）。

    经 utils/async_task.py 的 create_task_with_safe 托管，
    应用关闭时统一等待收尾。
    """
    # 示例：
    # from apps.tasks.content_review import review_pending_posts_loop
    # from utils.async_task import create_task_with_safe
    # create_task_with_safe(review_pending_posts_loop())


# ---------- 生命周期入口 ----------


async def startup() -> None:
    """应用启动：连接池 → 定时任务 → 持久任务。"""
    await init_db()
    register_schedulers()
    register_forever_tasks()


async def shutdown() -> None:
    """应用关闭：停调度器 → 等待后台任务 → 关闭 httpx → 关闭连接池。"""
    if scheduler is not None:
        scheduler.shutdown(wait=False)
    await shutdown_forever_task()
    await httpx_utils.close_httpx()
    if db.mysql_engine is not None:
        await db.mysql_engine.close()
