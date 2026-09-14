from configs.base_conf import BaseSettings


class TestSettings(BaseSettings):
    env = "test"

    db_name = "osc"
    db_port = 3206
    db_user = "kerwin"
    db_pass = "3l+JBr0iywj6LU1duyXaPQ=="
    db_host = "47.94.108.203"

    fast_go_client = "open_source_community"
    fast_go_secret_key = "jJjXhhs4i18sIIslZ1LRfankvXGnaBGZ"

    # fastgo 单点登录
    fast_go_website_url = "https://test-login.fescoadecco.com"  # fastgo 登录页地址，TODO: 填写实际值
    fast_go_api_url = "https://test-fastapi.fescoadecco.com"  # fastgo API 地址，TODO: 填写实际值
    mine_server = "http://localhost:8779"
