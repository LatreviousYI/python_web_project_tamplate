"""
项目中心业务层

- 同步云效组织成员（userId + name）到本地，供仓库列表 creatorUid → 姓名 匹配
- 获取代码组仓库列表（不落库，直接透传 + creatorUid 匹配姓名）
"""

from vorm import Session, col

from apps.model.common import KeyValue
from apps.model.project_center import YunxiaoUser
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


async def list_repositories(session: Session, page: int = 1, page_size: int = 20) -> dict:
    """获取代码组仓库列表（不落库），并把每个仓库的 creatorUid 匹配成创作者姓名。

    返回 {"totals": 总数量, "data": [仓库...]}：仓库原样透传 + 追加 creator_name 字段。
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

    data = [{**r, "creator_name": name_map.get(r.get("creatorUid"))} for r in repos]
    return {"totals": totals, "data": data}
