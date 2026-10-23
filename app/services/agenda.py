from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.erros import ErroValidacao
from app.models import Atribuicao, Escala, Turno
from app.schemas.agenda import AgendaTurno
from app.schemas.servidor import ServidorRead

PERIODO_MAXIMO_DIAS = 31


def validar_periodo_consulta(inicio: date, fim: date) -> None:
    if fim < inicio:
        raise ErroValidacao("A data final não pode ser anterior à data inicial.")
    if (fim - inicio).days + 1 > PERIODO_MAXIMO_DIAS:
        raise ErroValidacao(f"O período da consulta não pode exceder {PERIODO_MAXIMO_DIAS} dias.")


def consultar_agenda(
    db: Session,
    inicio: date,
    fim: date,
    servidor_id: int | None = None,
    setor_id: int | None = None,
) -> list[AgendaTurno]:
    validar_periodo_consulta(inicio, fim)
    consulta = (
        select(Turno)
        .join(Turno.escala)
        .where(Turno.data.between(inicio, fim))
        .options(
            joinedload(Turno.escala).joinedload(Escala.setor),
            selectinload(Turno.atribuicoes).selectinload(Atribuicao.servidor),
        )
        .order_by(Turno.data, Turno.hora_inicio, Turno.id)
    )
    if setor_id is not None:
        consulta = consulta.where(Escala.setor_id == setor_id)
    if servidor_id is not None:
        do_servidor = select(Atribuicao.turno_id).where(
            Atribuicao.servidor_id == servidor_id, Atribuicao.status == "confirmada"
        )
        consulta = consulta.where(Turno.id.in_(do_servidor))

    return [
        AgendaTurno(
            id=turno.id,
            escala_id=turno.escala_id,
            escala_nome=turno.escala.nome,
            setor_sigla=turno.escala.setor.sigla,
            data=turno.data,
            hora_inicio=turno.hora_inicio,
            hora_fim=turno.hora_fim,
            tipo=turno.tipo,
            vagas=turno.vagas,
            vagas_livres=turno.vagas_livres,
            servidores=[
                ServidorRead.model_validate(a.servidor)
                for a in turno.atribuicoes
                if a.status == "confirmada"
            ],
        )
        for turno in db.scalars(consulta)
    ]
