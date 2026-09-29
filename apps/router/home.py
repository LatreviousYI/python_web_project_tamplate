from fastapi import APIRouter

router = APIRouter(prefix="/home")


@router.get("/message")
async def ge():
    return "ok"


@router.get("/healthy")
async def healthy():
    return {"msg": "ok", "code": 200}
