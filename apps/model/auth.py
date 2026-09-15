from typing import Optional

from vorm import Field
from vorm.ddl import Index

from apps.model.base_field import BaseField


class User(BaseField):
    """SSO 用户（作者身份，以 user_id 为唯一主标识）。"""

    class Meta:
        table = "osc_user"
        indexes = [
            Index(fields=("user_id",), unique=True),
        ]

    user_name: str = Field(max_length=48, comment="用户名")
    name: Optional[str] = Field(default=None, max_length=100, nullable=True, comment="姓名")
    mobile: str = Field(max_length=24, comment="手机号")
    email: Optional[str] = Field(default=None, max_length=48, nullable=True, comment="邮箱")
    tenant: Optional[str] = Field(default=None, max_length=48, nullable=True, comment="租户")
    user_id: str = Field(max_length=200, comment="SSO 账号标识（fastgo accountCode）")
    avatar: Optional[str] = Field(default=None, max_length=500, nullable=True, comment="头像URL")
