from pathlib import Path


class BaseSettings:
    app_name = "open_source_community"
    # 为了解决create_task方法弱引用问题
    background_tasks = set()
    # 0表示开启,1表示关闭,在程序关闭时会更改为 1
    background_tasks_shutdown_stauts = 0
    # os.path.abspath 将相对路径转换为绝对路径
    # os.path.dirname 当前脚本所在目录
    basedir = Path(__file__).parent.parent.parent

    jwt_algorithm = "HS256"  # 加密算法
    access_token_expire_minutes = 1440  # token 有效期 1440
    jwt_secret_key = "91tf6f2f0bbb237143782736075b2t8d48bbacf6aafd6bee609be561d773db36"

    request_password = "xiaozhi_6"  # 请求时不需要登录token验证,但是需要安全验证,可以用这个密码
    request_password_hsah = "ab3f30418a590600ad9b6220ab5cc952fcbbb6424cfee44d7de2618b0110e717"  # AKS3HKH7KJSAJH@AS
