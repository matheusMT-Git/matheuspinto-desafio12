from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.dashboard import DashboardRead
from app.services import dashboard as servico
from app.utils import hoje, semana_de

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardRead)
def indicadores(
    inicio: date | None = None,
    fim: date | None = None,
    setor_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Sem período, usa a semana corrente."""
    segunda, domingo = semana_de(hoje())
    return servico.calcular_dashboard(db, inicio or segunda, fim or domingo, setor_id)
