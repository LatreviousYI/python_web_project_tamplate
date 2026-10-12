from apps.model.auth import User
from apps.model.common import DistributedLock, KeyValue
from apps.model.notification import Notification
from apps.model.post import Post, PostLike
from apps.model.reply import Reply, ReplyVote
from apps.model.project_center import Project, ProjectContributor, ProjectLike
from common.db import get_asynccontext_session
from utils import log_util


db_list = (User, Post, Reply, ReplyVote, PostLike, Notification, Project, ProjectContributor, ProjectLike, KeyValue, DistributedLock)


async def _backfill_null_timestamps(session, model) -> int:
    """回填历史脏数据里的 NULL created_at / updated_at，返回回填行数。

    BaseField 的 created_at / updated_at 已收紧为 NOT NULL，而 sync_table() 会为
    「模型要求 NOT NULL、库里仍允许 NULL」的列生成 ``ALTER TABLE ... MODIFY ... NOT NULL``。
    这两列没有 DEFAULT（值由 Python 侧 default_factory 提供），因此只要表里还残留 NULL 行，
    MySQL 严格模式下这条 ALTER 就会报 1138 (Invalid use of NULL value)，
    使 sync_db() 抛异常、应用直接起不来。

    所以必须在 sync_table() 之前先把 NULL 回填掉。表还不存在（首次建表）时跳过，
    由 sync_table() 负责建表。
    """
    fields = [
        field_name
        for field_name, info in model.__column_info__.items()
        if info.timestamp_behavior and not info.nullable
    ]
    if not fields:
        return 0

    dialect = session.dialect
    existing = await dialect.introspect_columns(model.__table__)
    if not existing:
        return 0

    table_sql = dialect.quote_identifier(model.__table__)
    changed = 0
    for field_name in fields:
        column = model.__columns__[field_name]
        current = existing.get(column.column_name.lower())
        if current is None:
            continue
        # 库里已经是 NOT NULL 就没有 NULL 行，无需扫描（首次迁移成功后每次启动都是零成本）
        if not current.is_nullable:
            continue
        column_sql = dialect.quote_identifier(column.column_name)
        rows = await session.execute_raw(
            f"UPDATE {table_sql} SET {column_sql} = NOW() WHERE {column_sql} IS NULL"
        )
        if rows:
            log_util.logger.warning(
                "回填历史 NULL 时间戳：%s.%s 共 %s 行", model.__table__, column.column_name, rows
            )
            changed += rows
    return changed


async def sync_db():
    """同步全部表结构。

    每张表先回填 NULL 时间戳，再执行 sync_table()，避免 NOT NULL 收紧 alter 失败。
    """
    async with get_asynccontext_session() as session:
        for model in db_list:
            await _backfill_null_timestamps(session, model)
            await model.sync_table(session.dialect)
