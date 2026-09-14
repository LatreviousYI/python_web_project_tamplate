import os
import uuid

from fastapi import UploadFile

from utils import oss


async def knowledge_upload_file_with_bytes_get_file_key(file: UploadFile, folder="open_source_community", is_rename=True):
    contents = await file.read()
    file_name = file.filename or "file"
    if is_rename:
        short_uuid = str(uuid.uuid4()).split("-")[0]
        _, file_extension = os.path.splitext(file_name)
        file_name = f"{short_uuid}{file_extension}"
    object_name = f"{folder}/{file_name}"  # folder = 'p9e'
    bucket = oss.create_bucket()
    file_key = await oss.upload_file_with_bytes_async_get_file_key(bucket, object_name, contents)
    return file_key
