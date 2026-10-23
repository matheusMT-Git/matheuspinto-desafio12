from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.servidor import ServidorRead
from app.services import servidores as servico

router = APIRouter(prefix="/servidores", tags=["servidores"])


@router.get("", response_model=list[ServidorRead])
def listar_servidores(
    setor_id: int | None = None, ativo: bool | None = None, db: Session = Depends(get_db)
):
    return servico.listar_servidores(db, setor_id, ativo)
