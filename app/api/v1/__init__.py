from fastapi import APIRouter

from app.api.v1 import atribuicoes, escalas, servidores

router = APIRouter(prefix="/api/v1")
router.include_router(escalas.router)
router.include_router(servidores.router)
router.include_router(atribuicoes.router)
