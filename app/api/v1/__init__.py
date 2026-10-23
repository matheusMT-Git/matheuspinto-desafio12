from fastapi import APIRouter

from app.api.v1 import agenda, atribuicoes, dashboard, escalas, servidores

router = APIRouter(prefix="/api/v1")
router.include_router(escalas.router)
router.include_router(servidores.router)
router.include_router(atribuicoes.router)
router.include_router(agenda.router)
router.include_router(dashboard.router)
