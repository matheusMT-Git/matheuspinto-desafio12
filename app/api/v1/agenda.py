from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.agenda import AgendaTurno
from app.services import agenda as servico

router = APIRouter(prefix="/agenda", tags=["agenda"])


@router.get("", response_model=list[AgendaTurno])
def consultar_agenda(
    inicio: date,
    fim: date,
    servidor_id: int | None = None,
    setor_id: int | None = None,
    db: Session = Depends(get_db),
):
    return servico.consultar_agenda(db, inicio, fim, servidor_id, setor_id)
