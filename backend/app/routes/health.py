from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/health")
def get_health_check():
    return JSONResponse({"status": "ok"})
