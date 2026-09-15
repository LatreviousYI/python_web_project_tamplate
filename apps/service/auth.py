"""
鉴权业务层

fastgo 单点登录：用 ticket 换取用户信息，按 accountCode 关联本地 User（不存在则创建），
返回本地 JWT（含用户主键 id + fast_token）。
DB 会话由路由通过 common.db.get_session 注入，当前阶段不连库、不执行。
"""

from vorm import Session

from apps.model.auth import User
from utils import fast_go, response_utils, tools
from utils.jwt import generate_token


async def fastgo_login(session: Session, ticket: str) -> dict:
    """fastgo 单点登录：ticket → 用户信息 → 本地 User（find-or-create）→ 本地 JWT。"""
    result = await fast_go.do_fastgo_check_ticket(ticket, True)

    if result.get("code") != 200:
        response_utils.abort(401, "fastgo 单点登录校验失败")
    account_info = tools.json_to_dict(result.get("userAccountInfo"))
    fast_token = result.get("fastToken")
    if not account_info or not fast_token:
        response_utils.abort(401, "fastgo 单点登录校验失败")

    account_code = account_info.get("accountCode")
    if not account_code:
        response_utils.abort(401, "fastgo 未返回账号标识")

    # 按 accountCode 关联本地用户，不存在则创建
    user = await session.query(User).filter(User.user_id == account_code).first()
    account_name = account_info.get("realName") or account_info.get("nickName")
    if user is None:
        user = User(
            user_id=account_code,
            user_name=account_info.get("userName") or "",
            name=account_name or None,
            mobile=account_info.get("mobilePhone") or "",
            email=account_info.get("email"),
            tenant=account_info.get("tenantName"),
        )
        await session.save(user)
    elif account_name:
        # 老用户登录时回填姓名（以 SSO 为准）
        user.name = account_name
        await session.save(user)

    # 本地 JWT：用户主键 id + fast_token
    token = generate_token({"user_id": user.id, "fast_token": fast_token})

    return {"token": token, "user": user}


async def fastgo_logout(fast_token: str) -> None:
    """fastgo 退出登录：调用 SSO 注销 fast_token（本地 JWT 由客户端丢弃）。"""
    await fast_go.login_out(fast_token)
