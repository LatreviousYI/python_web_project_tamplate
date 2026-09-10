from vorm import Field

from apps.model.base_field import BaseField


class User(BaseField):
    user_name: str = Field(max_length=200, comment="用户名")
