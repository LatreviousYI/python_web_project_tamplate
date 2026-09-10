from configs.base_conf import BaseSettings


class DevSettings(BaseSettings):
    env = "dev"

    db_name = "vrm"
    db_port = 3306
    db_user = "vrm"
    db_pass = "0O/sAR0HvuBCglze1Sg5ZQ=="
    db_host = "rm-uf6x1fd8n8493j0iw.mysql.rds.aliyuncs.com"
