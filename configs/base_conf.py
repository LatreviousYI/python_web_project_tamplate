from pathlib import Path


class BaseSettings:
    sec_key = ""
    env = ""
    app_name = "sme"
    basedir = Path(__file__).resolve().parent.parent

    server_host = "0.0.0.0"
    server_port = 8779

    # 0 表示运行中，1 表示应用正在关闭
    background_tasks_shutdown_stauts = 0

    jwt_algorithm = "HS256"
    access_token_expire_minutes = 1440

    cors_allow_origins = ["*"]
    cors_allow_credentials = False

    def __init__(self):
        self.background_tasks = set()
        self.cors_allow_origins = list(self.cors_allow_origins)
