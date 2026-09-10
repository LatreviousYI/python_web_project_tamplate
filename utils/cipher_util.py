"""
加解密工具模块

提供AES对称加密解密功能，使用CBC模式和PKCS7填充
"""

from base64 import b64encode, b64decode

from Crypto.Cipher import AES  # pip install pycryptodome
from Crypto.Util.Padding import pad, unpad

from configs import settings


class AESCipher:
    """AES加密解密类，支持128/192/256位密钥"""

    def __init__(self, key):
        """
        初始化加密器

        Args:
            key: 十六进制格式的密钥字符串
        """
        key_bytes = bytes.fromhex(key)
        if len(key_bytes) not in (16, 24, 32):
            raise ValueError("sec_key长度错误，应为16/24/32字节")
        self.key = key_bytes

    def encrypt(self, data):
        """
        加密数据

        Args:
            data: 待加密的字符串

        Returns:
            Base64编码的密文
        """
        cipher = AES.new(self.key, AES.MODE_ECB)
        ct_bytes = cipher.encrypt(pad(data.encode(), AES.block_size))
        return b64encode(ct_bytes).decode("utf-8")

    def decrypt(self, data):
        """
        解密数据

        Args:
            data: Base64编码的密文

        Returns:
            解密后的明文字符串
        """
        ct = b64decode(data)
        cipher = AES.new(self.key, AES.MODE_ECB)
        return unpad(cipher.decrypt(ct), AES.block_size).decode("utf-8")


# 全局加密器实例
sec_key = settings.sec_key
cipher = AESCipher(sec_key)


if __name__ == "__main__":
    import secrets

    # 生成新的十六进制密钥（32字节=256位）
    key_hex = secrets.token_hex(16)
    print(f"生成密钥: {key_hex}")

    # 测试加密解密
    passwd = "dinghfa4ngnuwyd8h3fq"
    encrypted = cipher.encrypt(passwd)
    print(f"加密: {encrypted}")

    decrypted = cipher.decrypt(encrypted)
    print(f"解密: {decrypted}")
