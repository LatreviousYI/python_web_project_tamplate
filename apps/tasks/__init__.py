"""
定时任务与后台常驻任务注册

- APScheduler：cron 定时任务（云效用户同步）
- asyncio 常驻任务：内容审核（持续循环，空闲休眠）
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from apps.tasks.content_review import review_pending_posts_loop
from apps.tasks.yunxiao_user import sync_yunxiao_user_job
from utils import async_task


def start_scheduler() -> AsyncIOScheduler:
    """创建并启动 APScheduler，注册 cron 定时任务。"""
    scheduler = AsyncIOScheduler()
    # 每天 0 点同步云效用户（用于仓库列表 creatorUid → 姓名的展示匹配）
    scheduler.add_job(
        sync_yunxiao_user_job,
        CronTrigger(hour=0, minute=0),
        id="sync_yunxiao_user",
        name="同步云效用户",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler


def start_forerver_loop():
    """启动内容审核常驻循环，返回可取消的任务。"""
    async_task.create_task_with_safe(review_pending_posts_loop())
