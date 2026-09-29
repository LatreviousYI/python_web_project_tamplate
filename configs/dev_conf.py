from configs.base_conf import BaseSettings


class DevSettings(BaseSettings):
    env = "dev"

    db_host = "rm-uf6x1fd8n8493j0iw.mysql.rds.aliyuncs.com"
    db_name = "vrm"
    db_port = 3306
    db_user = "vrm"
    db_pass = "dA/RLWdh2YUhSvorF+pjDA=="

    fast_go_client = "open_source_community"
    fast_go_secret_key = "jJjXhhs4i18sIIslZ1LRfankvXGnaBGZ"

    # fastgo 单点登录
    fast_go_website_url = "https://test-login.fescoadecco.com"  # fastgo 登录页地址，TODO: 填写实际值
    fast_go_api_url = "https://test-fastapi.fescoadecco.com"  # fastgo API 地址，TODO: 填写实际值

    mine_server = "https://test-api-ai.fescoadecco.com/osc"
