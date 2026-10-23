from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.erros import ErroConflito, ErroValidacao, NaoEncontrado
from app.models import Escala, Setor, Turno
from app.schemas.escala import EscalaCreate, StatusEscala
from app.schemas.turno import TurnoCreate

PERIODO_MAXIMO_DIAS = 31

TRANSICOES_STATUS: dict[str, set[str]] = {
    "rascunho": {"publicada"},
    "publicada": {"encerrada"},
    "encerrada": set(),
}


def _validar_periodo(inicio: date, fim: date) -> None:
    if fim < inicio:
        raise ErroValidacao("A data final não pode ser anterior à data inicial.")
    if (fim - inicio).days + 1 > PERIODO_MAXIMO_DIAS:
        raise ErroValidacao(f"O período da escala não pode exceder {PERIODO_MAXIMO_DIAS} dias.")


def _validar_turno(dados: TurnoCreate, inicio: date, fim: date) -> None:
    if not inicio <= dados.data <= fim:
        raise ErroValidacao(
            f"O turno de {dados.data:%d/%m/%Y} está fora do período da escala "
            f"({inicio:%d/%m/%Y} a {fim:%d/%m/%Y})."
        )
    if dados.vagas < 1:
        raise ErroValidacao("O turno deve ter ao menos 1 vaga.")
    if dados.hora_fim == dados.hora_inicio:
        raise ErroValidacao("O horário final do turno deve ser diferente do inicial.")
    if dados.hora_fim < dados.hora_inicio and dados.tipo != "noite":
        raise ErroValidacao(
            "O horário final do turno deve ser maior que o inicial "
            "(somente o turno da noite pode virar o dia)."
        )


def listar_setores(db: Session) -> list[Setor]:
    return list(db.scalars(select(Setor).order_by(Setor.nome)))


def criar_escala(db: Session, dados: EscalaCreate) -> Escala:
    """Cria a escala com seus turnos; se qualquer regra falhar, nada é gravado."""
    nome = dados.nome.strip()
    if not nome:
        raise ErroValidacao("Informe o nome da escala.")
    if db.get(Setor, dados.setor_id) is None:
        raise ErroValidacao("Setor informado não existe.")
    _validar_periodo(dados.data_inicio, dados.data_fim)
    for turno in dados.turnos:
        _validar_turno(turno, dados.data_inicio, dados.data_fim)

    escala = Escala(
        nome=nome,
        setor_id=dados.setor_id,
        data_inicio=dados.data_inicio,
        data_fim=dados.data_fim,
        status="rascunho",
    )
    escala.turnos = [Turno(**turno.model_dump()) for turno in dados.turnos]
    db.add(escala)
    db.commit()
    return escala


def listar_escalas(
    db: Session, setor_id: int | None = None, status: StatusEscala | None = None
) -> list[Escala]:
    consulta = select(Escala).order_by(Escala.data_inicio.desc(), Escala.id.desc())
    if setor_id is not None:
        consulta = consulta.where(Escala.setor_id == setor_id)
    if status is not None:
        consulta = consulta.where(Escala.status == status)
    return list(db.scalars(consulta))


def obter_escala(db: Session, escala_id: int) -> Escala:
    consulta = (
        select(Escala)
        .where(Escala.id == escala_id)
        .options(selectinload(Escala.turnos).selectinload(Turno.atribuicoes))
    )
    escala = db.scalars(consulta).one_or_none()
    if escala is None:
        raise NaoEncontrado("Escala não encontrada.")
    return escala


def alterar_status(db: Session, escala_id: int, novo_status: StatusEscala) -> Escala:
    escala = obter_escala(db, escala_id)
    if novo_status not in TRANSICOES_STATUS[escala.status]:
        raise ErroConflito(
            f"Não é possível mudar a escala de '{escala.status}' para '{novo_status}'."
        )
    escala.status = novo_status
    db.commit()
    return escala


def criar_turno(db: Session, escala_id: int, dados: TurnoCreate) -> Turno:
    escala = obter_escala(db, escala_id)
    if escala.status == "encerrada":
        raise ErroConflito("Não é possível incluir turnos em uma escala encerrada.")
    _validar_turno(dados, escala.data_inicio, escala.data_fim)
    turno = Turno(escala_id=escala.id, **dados.model_dump())
    db.add(turno)
    db.commit()
    db.expire(escala, ["turnos"])
    return turno
