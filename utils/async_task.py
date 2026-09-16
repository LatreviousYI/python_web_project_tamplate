"""
异步任务工具模块

提供安全的异步任务创建功能，用于后台任务的调度
"""

import asyncio

import configs
from utils import log_util


def create_task_with_safe(coro):
    """
    安全地创建异步任务并添加到后台任务管理

    该函数会：
    1. 创建异步任务
    2. 添加到FastAPI的background_tasks中管理
    3. 任务完成时自动从background_tasks中移除

    Args:
        coro: 协程对象

    Example:
        # 正确用法
        async def send_email():
            await smtp.send(...)

        # 传入协程对象（调用async函数会返回协程）
        create_task_with_safe(send_email())
        create_task_with_safe(send_email(user_id="123"))
    """
    coro_task = asyncio.create_task(coro)
    configs.settings.background_tasks.add(coro_task)
    coro_task.add_done_callback(configs.settings.background_tasks.discard)


def shutdown_forever_task():
    configs.settings.background_tasks_shutdown_stauts = 1
    while True:
        if not configs.settings.background_tasks:
            return
        else:
            log_util.logger.info(f"还有{len(configs.settings.background_tasks)}个任务未关闭")


class TaskQueue:
    def __init__(self, task_queue_limit=None):
        self.task_queue = set()
        self.task_queue_limit = task_queue_limit

    async def add_task(self, coro):
        if self.task_queue_limit:
            while len(self.task_queue) >= self.task_queue_limit:
                log_util.logger.info("队列已满,正在等待")
                await asyncio.sleep(1)
                continue
        log_util.logger.debug("增加任务")
        coro_task = asyncio.create_task(coro)
        self.task_queue.add(coro_task)
        coro_task.add_done_callback(self.task_queue.discard)
