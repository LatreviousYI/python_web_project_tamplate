"""
加解密工具模块

新密文使用 AES-GCM，nonce 和认证标签随密文一起保存。
"""

import secrets
from base64 import b64decode, b64encode

from Crypto.Cipher import AES  # pip install pycryptodome
from Crypto.Hash import SHA256
from Crypto.Protocol.KDF import HKDF

GCM_NONCE_LENGTH = 12
GCM_TAG_LENGTH = 16


def generate_sec_key() -> str:
    """生成 32 字节的十六进制 AES 密钥（64 个字符）。"""
    return secrets.token_hex(32)


def derive_key(master_key_hex: str, purpose: str, length: int = 32) -> bytes:
    """从 SEC_KEY 派生指定用途的子密钥。"""
    if not purpose:
        raise ValueError("密钥用途不能为空")
    master_key = bytes.fromhex(master_key_hex)
    derived_key = HKDF(master_key, length, b"", SHA256, context=purpose.encode("utf-8"))
    if not isinstance(derived_key, bytes):
        raise RuntimeError("派生密钥格式错误")
    return derived_key


class AESCipher:
    """AES 加密解密类，支持 128/192/256 位密钥。"""

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

    def encrypt(self, data: str) -> str:
        """
        使用 AES-GCM 加密数据。

        Args:
            data: 待加密的字符串

        Returns:
            包含 nonce、密文和 tag 的 Base64 字符串
        """
        nonce = secrets.token_bytes(GCM_NONCE_LENGTH)
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce, mac_len=GCM_TAG_LENGTH)
        ciphertext, tag = cipher.encrypt_and_digest(data.encode("utf-8"))
        payload = nonce + ciphertext + tag
        return b64encode(payload).decode("ascii")

    def decrypt(self, data: str) -> str:
        """
        使用 AES-GCM 解密数据。

        Args:
            data: 包含 nonce、密文和 tag 的 Base64 字符串

        Returns:
            解密后的明文字符串
        """
        try:
            payload = b64decode(data, validate=True)
        except ValueError as exc:
            raise ValueError("密文格式错误") from exc

        if len(payload) < GCM_NONCE_LENGTH + GCM_TAG_LENGTH:
            raise ValueError("密文格式错误")

        nonce = payload[:GCM_NONCE_LENGTH]
        ciphertext = payload[GCM_NONCE_LENGTH:-GCM_TAG_LENGTH]
        tag = payload[-GCM_TAG_LENGTH:]
        cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce, mac_len=GCM_TAG_LENGTH)

        try:
            plaintext = cipher.decrypt_and_verify(ciphertext, tag)
            return plaintext.decode("utf-8")
        except (ValueError, UnicodeDecodeError) as exc:
            raise ValueError("密文校验失败或密钥错误") from exc


class _LazyCipher:
    """延迟读取 SEC_KEY，使密钥生成函数不依赖现有配置。"""

    def __init__(self):
        self._cipher: AESCipher | None = None

    def _get_cipher(self) -> AESCipher:
        if self._cipher is None:
            from configs import settings

            self._cipher = AESCipher(settings.sec_key)
        return self._cipher

    def encrypt(self, data: str) -> str:
        return self._get_cipher().encrypt(data)

    def decrypt(self, data: str) -> str:
        return self._get_cipher().decrypt(data)


# 保留原有调用方式：cipher.encrypt() / cipher.decrypt()
cipher = _LazyCipher()
