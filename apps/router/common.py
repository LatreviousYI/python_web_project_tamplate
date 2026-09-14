from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import RedirectResponse

from apps import dependencies
from apps.service.common import knowledge_upload_file_with_bytes_get_file_key
import configs
from utils import oss, response_utils

router = APIRouter(prefix="/common")


@router.post("/upload/file")
async def upload_file(file: UploadFile, user_id: int = Depends(dependencies.get_current_user)):
    filekey = await knowledge_upload_file_with_bytes_get_file_key(file)
    return response_utils.ApiResponse(data=f"{configs.settings.mine_server}/api/v1/common/get/file?file_key={filekey}")


@router.get("/get/file")
async def get_file(file_key: str):
    bucket = oss.create_bucket()
    oss_url = await oss.set_file_time_async(bucket, file_key, 60 * 60 * 2)
    return RedirectResponse(oss_url)
