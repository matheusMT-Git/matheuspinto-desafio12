from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Servidor


def listar_servidores(
    db: Session, setor_id: int | None = None, ativo: bool | None = None
) -> list[Servidor]:
    consulta = select(Servidor).order_by(Servidor.nome)
    if setor_id is not None:
        consulta = consulta.where(Servidor.setor_id == setor_id)
    if ativo is not None:
        consulta = consulta.where(Servidor.ativo == ativo)
    return list(db.scalars(consulta))
