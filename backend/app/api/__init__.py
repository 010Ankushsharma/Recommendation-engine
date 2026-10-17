from fastapi import APIRouter
from app.api.routes.recommendations import router as recommendations_router

router = APIRouter()

router.include_router(recommendations_router)
