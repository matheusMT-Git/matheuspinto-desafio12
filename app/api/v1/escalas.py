from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.escala import (
    EscalaCreate,
    EscalaDetalhe,
    EscalaRead,
    EscalaStatusUpdate,
    StatusEscala,
)
from app.schemas.turno import TurnoCreate, TurnoRead
from app.services import escalas as servico

router = APIRouter(prefix="/escalas", tags=["escalas"])


@router.post("", response_model=EscalaDetalhe, status_code=201)
def cadastrar_escala(dados: EscalaCreate, db: Session = Depends(get_db)):
    return servico.criar_escala(db, dados)


@router.get("", response_model=list[EscalaRead])
def listar_escalas(
    setor_id: int | None = None,
    status: StatusEscala | None = None,
    db: Session = Depends(get_db),
):
    return servico.listar_escalas(db, setor_id, status)


@router.get("/{escala_id}", response_model=EscalaDetalhe)
def detalhar_escala(escala_id: int, db: Session = Depends(get_db)):
    return servico.obter_escala(db, escala_id)


@router.patch("/{escala_id}/status", response_model=EscalaRead)
def alterar_status(escala_id: int, dados: EscalaStatusUpdate, db: Session = Depends(get_db)):
    return servico.alterar_status(db, escala_id, dados.status)


@router.post("/{escala_id}/turnos", response_model=TurnoRead, status_code=201)
def criar_turno(escala_id: int, dados: TurnoCreate, db: Session = Depends(get_db)):
    return servico.criar_turno(db, escala_id, dados)
