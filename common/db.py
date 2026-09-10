from vorm import engine

import configs
from utils import cipher_util


mysql_engine = None


async def get_engine():
    global mysql_engine
    mysql_engine = await engine.create_mysql_engine(
        host=configs.settings.db_host,
        port=3306,
        user=configs.settings.db_user,
        password=cipher_util.cipher.decrypt(configs.settings.db_pass),
        database=configs.settings.db_name,
        minsize=10,
        maxsize=20,
    )
