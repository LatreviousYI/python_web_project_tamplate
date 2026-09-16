"""
内容审核常驻任务

常驻循环处理待审核（pending）的文章 / 问答：调用 AI 内容审核（utils.betteryeah_utils.verfiy_content），
通过则自动发布，不通过则打回草稿。无待审核内容时休眠 60 秒再继续扫。
"""

import asyncio

from apps.service import post as post_service
from apps.service.lock import acquire_lock
from common.db import get_asynccontext_session
import configs
from utils import log_util

# 单批最多处理条数，防止积压过多导致单批耗时过长；剩余留待下一轮继续
_BATCH_SIZE = 50
# 空闲（无待审核内容）时的轮询间隔（秒）
_IDLE_SLEEP_SECONDS = 10
_LOCK_KEY = "review_pending_posts"


async def review_pending_posts_loop() -> None:
    """常驻循环：持续审核待发布内容，空闲时休眠 60 秒。"""

    if not await acquire_lock(_LOCK_KEY, "system", 60):
        return
    while True:
        if configs.settings.background_tasks_shutdown_stauts == 1:
            log_util.logger.debug("程序关闭")
            return
        async with get_asynccontext_session() as session:
            # 分布式锁：多实例时保证同一时刻只有一个实例在审核；每批获取、处理完立即释放
            try:
                count = await post_service.review_pending_posts(session, _BATCH_SIZE)
                if count:
                    log_util.logger.info("内容审核完成，本次处理 %s 条", count)
            except Exception:
                log_util.logger.exception("内容审核处理失败")
                count = 0
            # 有任务就继续处理下一批，无任务才休眠
            if count == 0:
                await asyncio.sleep(_IDLE_SLEEP_SECONDS)
