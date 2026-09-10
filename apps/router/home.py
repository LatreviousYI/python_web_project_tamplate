from fastapi import APIRouter

router = APIRouter(prefix="/home")


@router.get("/message")
async def ge():
    return "ok"
