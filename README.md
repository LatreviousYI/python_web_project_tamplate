阿里云效令牌过期创建
https://account-devops.aliyun.com/settings/personalAccessToken

令牌过期后需要获取新的令牌保存到数据库中
表名 osc_kv
key=ali_yunxiao_token
value = utils\cipher_util.py.cipher.encrypt(明文)