from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.atribuicao import AtribuicaoCreate, AtribuicaoRead
from app.services import atribuicoes as servico

router = APIRouter(tags=["atribuições"])


@router.post("/turnos/{turno_id}/atribuicoes", response_model=AtribuicaoRead, status_code=201)
def atribuir_turno(turno_id: int, dados: AtribuicaoCreate, db: Session = Depends(get_db)):
    return servico.atribuir(db, turno_id, dados.servidor_id)


@router.delete("/atribuicoes/{atribuicao_id}", status_code=204)
def cancelar_atribuicao(atribuicao_id: int, db: Session = Depends(get_db)) -> Response:
    servico.cancelar(db, atribuicao_id)
    return Response(status_code=204)
