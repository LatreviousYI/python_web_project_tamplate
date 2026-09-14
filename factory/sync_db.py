from apps.model.auth import User
from apps.model.post import Post
from apps.model.reply import Reply, ReplyVote
from common.db import get_engine


db_list = (User, Post, Reply, ReplyVote)


async def sync_db():
    engine = await get_engine()
    session = engine.session()
    try:
        for model in db_list:
            await model.sync_table(session.dialect)
    finally:
        await session.close()
