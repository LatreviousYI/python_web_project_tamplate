import asyncio
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import unquote, urlparse

import oss2

from configs import settings
from utils.cipher_util import cipher

bucket = None


# 创建Bucket对象
def create_bucket():
    global bucket
    if not bucket:
        auth = oss2.Auth(
            cipher.decrypt(settings.oss_access_key_id),
            cipher.decrypt(settings.oss_access_key_secret),
        )
        bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)
    return bucket


# 创建OSS存储空间
def create_oss(bucket):
    bucket.create_bucket(oss2.models.BUCKET_ACL_PRIVATE)
    return bucket


def upload_file_to_oss(bucket: oss2.Bucket, oss_name, local_file_path):
    expiration = 60 * 60 * 24 * 3650
    # oss_name is 'p9e/birth.jpg'
    bucket.put_object_from_file(oss_name, local_file_path)
    file_url = bucket.sign_url("GET", oss_name, expiration, slash_safe=True)
    return file_url


def upload_file_to_oss_get_name_key(bucket: oss2.Bucket, oss_name, local_file_path):
    bucket.put_object_from_file(oss_name, local_file_path)
    return oss_name


def upload_file_with_bytes_get_name_key(bucket: oss2.Bucket, file_name, file_bytes):
    bucket.put_object(file_name, file_bytes)
    return file_name


def upload_image_with_bytes(bucket: oss2.Bucket, image_bytes, image_name):
    expiration = 60 * 60 * 24 * 3650
    bucket.put_object(image_name, image_bytes)
    file_url = bucket.sign_url("GET", image_name, expiration, slash_safe=True)
    return file_url


def set_file_time(bucket: oss2.Bucket, oss_name, expiration: int = None):
    if not expiration:
        expiration = 60 * 60 * 24 * 3650
    # oss_name is 'p9e/birth.jpg'
    file_url = bucket.sign_url("GET", oss_name, expiration, slash_safe=True)
    return file_url


async def create_oss_async(bucket):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, create_oss, bucket)


async def upload_file_to_oss_async(bucket, oss_name, local_file_path):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, upload_file_to_oss, bucket, oss_name, local_file_path)


async def upload_file_to_oss_async_get_name_key(bucket, oss_name, local_file_path):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, upload_file_to_oss_get_name_key, bucket, oss_name, local_file_path)


async def upload_file_with_bytes_async_get_file_key(bucket, file_name, file_bytes):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, upload_file_with_bytes_get_name_key, bucket, file_name, file_bytes)


async def set_file_time_async(bucket, oss_name, expiration=None):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, set_file_time, bucket, oss_name, expiration)


async def upload_image_with_bytes_async(bucket, image_bytes, image_name):
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as pool:
        return await loop.run_in_executor(pool, upload_image_with_bytes, bucket, image_bytes, image_name)


def get_key(oss_url_or_key: str):
    """
    description: 处理数据库中已有的oss url,因为旧原因,数据库中存在完整的oss url连接可能会造成时间过期,资源失效,所以重新用key获取新的链接
    param {str} oss_url_or_key
    return {*}
    """
    if "http" in oss_url_or_key:
        url_p = urlparse(unquote(oss_url_or_key))
        if url_p.path.startswith("/"):
            return url_p.path[1:]
    return oss_url_or_key
