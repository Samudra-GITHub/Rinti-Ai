from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "assistant": "Rinti",
        "version": "0.2.0"
    }