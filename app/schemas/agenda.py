from app.schemas.servidor import ServidorRead
from app.schemas.turno import TurnoRead


class AgendaTurno(TurnoRead):
    escala_nome: str
    setor_sigla: str
    servidores: list[ServidorRead]
