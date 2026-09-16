"""
云效用户同步定时任务

每天 0 点拉取阿里云效组织全部成员，只保存 userId + name 到本地，
用于后续代码仓库列表中 creatorUid → 姓名 的展示匹配。
"""

from apps.service import project_center as yunxiao_user_service
from apps.service.lock import acquire_lock
from common.db import get_asynccontext_session
from utils import log_util


async def sync_yunxiao_user_job() -> None:
    """定时任务入口：用独立会话拉取并落库云效用户。"""
    if not await acquire_lock("sync_yunxiao_user_job", "system", 60):
        return
    try:
        async with get_asynccontext_session() as session:
            count = await yunxiao_user_service.sync_yunxiao_users(session)
            log_util.logger.info(f"云效用户同步完成，新增/更新 {count} 条")
    except Exception as e:
        log_util.logger.error("云效同步失败")
        log_util.logger.exception(e)
    finally:
        await session.close()
