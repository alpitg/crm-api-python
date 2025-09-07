from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def create_user():
   return {"ping ok": True}
