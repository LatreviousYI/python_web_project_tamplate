"""
应用级依赖

集中定义供路由复用的 FastAPI 依赖。

当前鉴权为 SSO-ready 占位：假定公司 SSO 已发放 JWT（payload 含用户主键 id，int），
这里仅解析并返回该用户 id。待真实 SSO（票据换取）文档到位后，
仅需替换 get_current_user 内部实现，路由 / 服务 / 模型层均无需改动。
"""

from fastapi import Depends

from utils.jwt import decode_token_get_info, verify_token, verify_token_optional


async def get_current_user(user_id: int = Depends(verify_token)) -> int:
    """当前登录用户，返回用户主键 id（osc_user.id，int）。"""
    return user_id


async def get_optional_user(user_id: int | None = Depends(verify_token_optional)) -> int | None:
    """可选鉴权：已登录返回用户主键 id，未登录 / 非法 token 返回 None。"""
    return user_id


async def get_current_token_info(token_info: dict = Depends(decode_token_get_info)) -> dict:
    """当前登录用户的 JWT payload（含 user_id、fast_token 等），供需要完整 token 信息的接口使用。"""
    return token_info
