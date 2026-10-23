from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.erros import ErroConflito, ErroValidacao, NaoEncontrado
from app.models import Atribuicao, Servidor, Turno


def _intervalo(turno: Turno) -> tuple[datetime, datetime]:
    """Início e fim do turno; o turno que vira o dia termina na data seguinte."""
    inicio = datetime.combine(turno.data, turno.hora_inicio)
    fim = datetime.combine(turno.data, turno.hora_fim)
    if turno.hora_fim <= turno.hora_inicio:
        fim += timedelta(days=1)
    return inicio, fim


def obter_turno(db: Session, turno_id: int) -> Turno:
    consulta = (
        select(Turno)
        .where(Turno.id == turno_id)
        .options(selectinload(Turno.atribuicoes).selectinload(Atribuicao.servidor))
    )
    turno = db.scalars(consulta).one_or_none()
    if turno is None:
        raise NaoEncontrado("Turno não encontrado.")
    return turno


def _turno_em_choque(db: Session, servidor_id: int, turno: Turno) -> Turno | None:
    """Turno confirmado do servidor com horário sobreposto ao informado, se houver."""
    inicio, fim = _intervalo(turno)
    consulta = (
        select(Turno)
        .join(Atribuicao, Atribuicao.turno_id == Turno.id)
        .where(
            Atribuicao.servidor_id == servidor_id,
            Atribuicao.status == "confirmada",
            Turno.id != turno.id,
            # turnos de um dia antes (viram o dia) até um dia depois podem se sobrepor
            Turno.data.between(turno.data - timedelta(days=1), turno.data + timedelta(days=1)),
        )
    )
    for outro in db.scalars(consulta):
        outro_inicio, outro_fim = _intervalo(outro)
        if inicio < outro_fim and outro_inicio < fim:
            return outro
    return None


def atribuir(db: Session, turno_id: int, servidor_id: int) -> Atribuicao:
    turno = obter_turno(db, turno_id)
    servidor = db.get(Servidor, servidor_id)
    if servidor is None:
        raise NaoEncontrado("Servidor não encontrado.")
    if not servidor.ativo:
        raise ErroValidacao("Servidor inativo não pode ser escalado.")
    if turno.escala.status == "encerrada":
        raise ErroConflito("Não é possível atribuir turnos de uma escala encerrada.")

    existente = next((a for a in turno.atribuicoes if a.servidor_id == servidor_id), None)
    if existente is not None and existente.status == "confirmada":
        raise ErroConflito("O servidor já está atribuído a este turno.")

    choque = _turno_em_choque(db, servidor_id, turno)
    if choque is not None:
        raise ErroConflito(
            f"Choque de horário: o servidor já está escalado em {choque.data:%d/%m/%Y} "
            f"das {choque.hora_inicio:%H:%M} às {choque.hora_fim:%H:%M}."
        )
    if turno.vagas_livres <= 0:
        raise ErroConflito("Turno sem vagas.")

    if existente is not None:  # reativa a atribuição cancelada (par turno/servidor é único)
        existente.status = "confirmada"
        atribuicao = existente
    else:
        atribuicao = Atribuicao(turno_id=turno.id, servidor_id=servidor_id, status="confirmada")
        db.add(atribuicao)
    db.commit()
    db.expire(turno, ["atribuicoes"])
    return atribuicao


def cancelar(db: Session, atribuicao_id: int) -> Atribuicao:
    atribuicao = db.get(Atribuicao, atribuicao_id)
    if atribuicao is None:
        raise NaoEncontrado("Atribuição não encontrada.")
    atribuicao.status = "cancelada"
    db.commit()
    db.expire(atribuicao.turno, ["atribuicoes"])
    return atribuicao
