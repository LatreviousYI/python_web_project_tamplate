# from apps.model.auth import User
# from apps.model.common import DistributedLock, KeyValue
# from apps.model.notification import Notification
# from apps.model.post import Post, PostLike
# from apps.model.reply import Reply, ReplyVote
# from apps.model.project_center import Project, ProjectContributor, ProjectLike
# from common.db import get_asynccontext_session
# from utils import log_util


# db_list = ()
# # db_list = (User, Post, Reply, ReplyVote, PostLike, Notification, Project, ProjectContributor, ProjectLike, KeyValue, DistributedLock)


# async def sync_db():
#     """同步全部表结构。

#     每张表先回填 NULL 时间戳，再执行 sync_table()，避免 NOT NULL 收紧 alter 失败。
#     """
#     async with get_asynccontext_session() as session:
#         for model in db_list:
#             await model.sync_table(session.dialect)
