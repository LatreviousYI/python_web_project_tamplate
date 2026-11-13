from configs.base_conf import BaseSettings


class DevSettings(BaseSettings):
    env = "dev"

    db_host = ""
    db_port = 3306
    db_user = ""
    db_pass = ""  # AES-GCM 密文
    db_name = ""
    db_pool_min_size = 1
    db_pool_max_size = 5

