import os
from functools import lru_cache

from dotenv import load_dotenv

from configs.dev_conf import DevSettings
from configs.prod_conf import ProdSettings
from configs.test_conf import TestSettings
from configs.uat_conf import UatSettings

config = {
    "dev": DevSettings,
    "test": TestSettings,
    "uat": UatSettings,
    "prod": ProdSettings,
}


@lru_cache()
def get_settings():
    load_dotenv()
    config_name = os.getenv("APP_ENV", "prod")
    sec_key = os.environ["SEC_KEY"]
    configs = config[config_name]()  # oop
    setattr(configs, "sec_key", sec_key)
    return configs


settings: DevSettings = get_settings()
