"""
定时任务注册与调度

基于 APScheduler（AsyncIOScheduler），在应用 lifespan 启动 / 关闭时随进程一起启停。
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from apps.tasks.yunxiao_user import sync_yunxiao_user_job


def start_scheduler() -> AsyncIOScheduler:
    """创建并启动调度器，注册所有定时任务。"""
    scheduler = AsyncIOScheduler()
    # 每天 0 点同步云效用户（用于仓库列表 creatorUid → 姓名的展示匹配）
    scheduler.add_job(
        sync_yunxiao_user_job,
        CronTrigger(hour=10, minute=40),
        id="sync_yunxiao_user",
        name="同步云效用户",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
