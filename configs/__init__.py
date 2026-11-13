import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from configs.base_conf import BaseSettings
from configs.dev_conf import DevSettings
from configs.prod_conf import ProdSettings
from configs.test_conf import TestSettings
from configs.uat_conf import UatSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent

config = {
    "dev": DevSettings,
    "test": TestSettings,
    "uat": UatSettings,
    "prod": ProdSettings,
}


@lru_cache()
def get_settings() -> BaseSettings:
    """按根目录 .env 和应用环境创建配置单例。"""
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    config_name = os.getenv("APP_ENV")
    if not config_name:
        raise RuntimeError("缺少 APP_ENV，请在项目根目录 .env 中配置")

    settings_class = config.get(config_name)
    if settings_class is None:
        supported = ", ".join(config)
        raise RuntimeError(f"不支持的 APP_ENV={config_name}，可选值: {supported}")

    sec_key = os.getenv("SEC_KEY")
    if not sec_key:
        generate_command = 'uv run python -c "from utils.cipher_util import generate_sec_key; print(generate_sec_key())"'
        raise RuntimeError(f"缺少 SEC_KEY，可执行 `{generate_command}` 生成")

    try:
        key_length = len(bytes.fromhex(sec_key))
    except ValueError as exc:
        raise RuntimeError("SEC_KEY 必须是十六进制字符串") from exc
    if key_length not in (16, 24, 32):
        raise RuntimeError("SEC_KEY 长度错误，应为 16、24 或 32 字节")

    settings_instance = settings_class()
    settings_instance.sec_key = sec_key
    return settings_instance


settings: BaseSettings = get_settings()
