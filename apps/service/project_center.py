"""
项目中心业务层

- 同步云效组织成员（userId + name）到本地，供仓库列表 creatorUid → 姓名 匹配
- 获取代码组仓库列表（不落库，直接透传 + creatorUid 匹配姓名）
"""

from vorm import Session, col

from apps.model.common import KeyValue
from apps.model.project_center import ProjectLike, YunxiaoUser
from utils import ali_yunxiao, cipher_util, log_util

_PERPAGE = 100  # 每页拉取条数，可按云效接口上限调整
_TOKEN_KEY = "ali_yunxiao_token"  # osc_kv 中存放云效 token 的 key（值已加密）


async def _get_ali_yunxiao_token(session: Session) -> str | None:
    """从 osc_kv 读取并解密云效 token，未配置时返回 None。"""
    row = await session.query(KeyValue).filter(KeyValue.key == _TOKEN_KEY).first()
    if row is None:
        log_util.logger.error("云效 token 未配置（osc_kv 缺少 ali_yunxiao_token）")
        return None
    return cipher_util.cipher.decrypt(row.value)


async def sync_yunxiao_users(session: Session) -> int:
    """分页拉取云效全部成员并落库，返回新增 / 更新的条数。

    按 userId 幂等 upsert：已存在则更新 name，不存在则插入；不做删除（保留历史姓名兜底）。
    """
    token = await _get_ali_yunxiao_token(session)
    if not token:
        return 0

    existing_map = {u.user_id: u for u in await session.query(YunxiaoUser).all()}
    changed = 0
    page = 1
    while True:
        users = await ali_yunxiao.get_ali_yunxiao_user(token, page=page, perpage=_PERPAGE)
        if not users:
            break  # 空页 = 已拉完
        for item in users:
            uid = item.get("userId")
            name = item.get("name") or ""
            if not uid:
                continue
            rec = existing_map.get(uid)
            if rec is None:
                new_rec = YunxiaoUser(user_id=uid, name=name)
                await session.save(new_rec)
                existing_map[uid] = new_rec
                changed += 1
            elif rec.name != name:
                rec.name = name
                await session.save(rec)
                changed += 1
        page += 1
    return changed


async def list_repositories(session: Session, page: int = 1, page_size: int = 20, user_id: int | None = None) -> dict:
    """获取代码组仓库列表（不落库），并补充 creator_name / like_count / liked。

    返回 {"totals": 总数量, "data": [仓库...]}：仓库原样透传 + 追加 creator_name、like_count、liked 字段。
    总数量取自响应头 x-total。
    """
    token = await _get_ali_yunxiao_token(session)
    if not token:
        return {"totals": 0, "data": []}

    response = await ali_yunxiao.get_group_repositories(token, page=page, perpage=page_size)
    repos = response.json()
    totals = int(response.headers.get("x-total") or 0)

    # 批量匹配 creatorUid → 姓名（避免逐条 N+1）
    creator_uids = {r.get("creatorUid") for r in repos if r.get("creatorUid")}
    name_map: dict[str, str] = {}
    if creator_uids:
        users = await session.query(YunxiaoUser).filter(col(YunxiaoUser.user_id).in_(creator_uids)).all()
        name_map = {u.user_id: u.name for u in users}

    project_ids = [r.get("id") for r in repos if r.get("id") is not None]
    count_map, liked_set = await _project_like_stats(session, project_ids, user_id)

    data = [
        {**r, "creator_name": name_map.get(r.get("creatorUid")), "like_count": count_map.get(r.get("id"), 0), "liked": r.get("id") in liked_set}
        for r in repos
    ]
    return {"totals": totals, "data": data}


async def _project_like_stats(session: Session, project_ids: list[int], user_id: int | None) -> tuple[dict[int, int], set[int]]:
    """一次查询批量统计每个项目的点赞数与当前用户是否已赞。"""
    if not project_ids:
        return {}, set()
    likes = await session.query(ProjectLike).filter(col(ProjectLike.project_id).in_(project_ids)).all()
    count_map: dict[int, int] = {}
    liked_set: set[int] = set()
    for like in likes:
        count_map[like.project_id] = count_map.get(like.project_id, 0) + 1
        if user_id is not None and like.user_id == user_id:
            liked_set.add(like.project_id)
    return count_map, liked_set


async def like_project(session: Session, project_id: int, user_id: int) -> dict:
    """项目点赞 / 取消赞（切换式），返回 {"liked": bool, "like_count": int}。"""
    existing = await session.query(ProjectLike).filter(ProjectLike.project_id == project_id, ProjectLike.user_id == user_id).first()
    if existing is None:
        await session.save(ProjectLike(project_id=project_id, user_id=user_id))
    else:
        await session.delete(existing)
    liked = existing is None
    like_count = await session.query(ProjectLike).filter(ProjectLike.project_id == project_id).count()
    return {"liked": liked, "like_count": like_count}


async def get_repository_detail(session: Session, project_id: int, user_id: int | None = None) -> dict | None:
    """获取单个仓库详情，并补充 like_count / liked。token 未配置时返回 None。"""
    token = await _get_ali_yunxiao_token(session)
    if not token:
        return None
    detail = await ali_yunxiao.get_group_repositories_detail(token, project_id)
    count_map, liked_set = await _project_like_stats(session, [project_id], user_id)
    return {**detail, "like_count": count_map.get(project_id, 0), "liked": project_id in liked_set}
