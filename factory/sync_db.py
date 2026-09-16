from apps.model.auth import User
from apps.model.common import DistributedLock, KeyValue
from apps.model.post import Post, PostLike
from apps.model.reply import Reply, ReplyVote
from apps.model.project_center import ProjectLike, YunxiaoUser
from apps.service.lock import acquire_lock
from common.db import get_asynccontext_session


db_list = (User, Post, Reply, ReplyVote, PostLike, YunxiaoUser, ProjectLike, KeyValue, DistributedLock)


async def sync_db():
    async with get_asynccontext_session() as session:
        if not await acquire_lock("sync_db", "system", 60):
            return
        for model in db_list:
            await model.sync_table(session.dialect)
