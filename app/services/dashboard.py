from datetime import date, timedelta

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.models import Atribuicao, Escala, Turno
from app.schemas.dashboard import (
    DashboardRead,
    TurnoComVaga,
    VagasIndicador,
    VagasPorDia,
)
from app.services.agenda import validar_periodo_consulta

# Escalas encerradas ficam fora de todos os indicadores.
STATUS_PROGRAMADOS = ("publicada", "rascunho")
LIMITE_CRITICO = 50
LIMITE_ALERTA = 80


def _nivel(ocupacao: int, total: int) -> str:
    if total == 0 or ocupacao >= LIMITE_ALERTA:
        return "normal"
    return "critico" if ocupacao < LIMITE_CRITICO else "alerta"


def calcular_dashboard(
    db: Session, inicio: date, fim: date, setor_id: int | None = None
) -> DashboardRead:
    """Indicadores do período por consultas agregadas (sem carregar os registros)."""
    validar_periodo_consulta(inicio, fim)
    filtros = [Turno.data.between(inicio, fim), Escala.status.in_(STATUS_PROGRAMADOS)]
    if setor_id is not None:
        filtros.append(Escala.setor_id == setor_id)
    confirmada = Atribuicao.status == "confirmada"

    turnos_programados, vagas_total = db.execute(
        select(func.count(Turno.id), func.coalesce(func.sum(Turno.vagas), 0))
        .join(Turno.escala)
        .where(*filtros)
    ).one()
    ocupadas, pessoas = db.execute(
        select(func.count(Atribuicao.id), func.count(distinct(Atribuicao.servidor_id)))
        .join(Atribuicao.turno)
        .join(Turno.escala)
        .where(*filtros, confirmada)
    ).one()

    ocupacao = round(ocupadas * 100 / vagas_total) if vagas_total else 0
    vagas = VagasIndicador(
        total=vagas_total,
        ocupadas=ocupadas,
        livres=vagas_total - ocupadas,
        ocupacao_percentual=ocupacao,
        nivel=_nivel(ocupacao, vagas_total),
    )

    total_por_dia = {
        dia: total
        for dia, total in db.execute(
            select(Turno.data, func.sum(Turno.vagas))
            .join(Turno.escala)
            .where(*filtros)
            .group_by(Turno.data)
        ).tuples()
    }
    ocupadas_por_dia = {
        dia: ocup
        for dia, ocup in db.execute(
            select(Turno.data, func.count(Atribuicao.id))
            .join(Atribuicao.turno)
            .join(Turno.escala)
            .where(*filtros, confirmada)
            .group_by(Turno.data)
        ).tuples()
    }
    serie = []
    for deslocamento in range((fim - inicio).days + 1):
        dia = inicio + timedelta(days=deslocamento)
        total = total_por_dia.get(dia, 0)
        ocup = ocupadas_por_dia.get(dia, 0)
        serie.append(VagasPorDia(data=dia, total=total, ocupadas=ocup, livres=total - ocup))

    ocupadas_turno = func.count(Atribuicao.id)
    abertos = db.execute(
        select(Turno, Escala.nome, ocupadas_turno)
        .join(Turno.escala)
        .outerjoin(Atribuicao, (Atribuicao.turno_id == Turno.id) & confirmada)
        .where(*filtros)
        .group_by(Turno.id, Escala.id)
        .having(Turno.vagas - ocupadas_turno > 0)
        .order_by(Turno.data, Turno.hora_inicio, Turno.id)
    ).tuples()
    turnos_com_vaga = [
        TurnoComVaga(
            id=turno.id,
            escala_id=turno.escala_id,
            escala_nome=escala_nome,
            data=turno.data,
            hora_inicio=turno.hora_inicio,
            hora_fim=turno.hora_fim,
            tipo=turno.tipo,
            vagas=turno.vagas,
            vagas_livres=turno.vagas - ocup,
        )
        for turno, escala_nome, ocup in abertos
    ]

    return DashboardRead(
        inicio=inicio,
        fim=fim,
        setor_id=setor_id,
        turnos_programados=turnos_programados,
        pessoas_escaladas=pessoas,
        vagas=vagas,
        serie_por_dia=serie,
        turnos_com_vaga=turnos_com_vaga,
    )
