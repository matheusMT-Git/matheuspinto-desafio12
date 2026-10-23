from fastapi import APIRouter

from app.api.v1 import escalas

router = APIRouter(prefix="/api/v1")
router.include_router(escalas.router)
