from datetime import date, time
from typing import Literal

from pydantic import BaseModel


class VagasIndicador(BaseModel):
    total: int
    ocupadas: int
    livres: int
    ocupacao_percentual: int
    nivel: Literal["normal", "alerta", "critico"]


class VagasPorDia(BaseModel):
    data: date
    total: int
    ocupadas: int
    livres: int


class TurnoComVaga(BaseModel):
    id: int
    escala_id: int
    escala_nome: str
    data: date
    hora_inicio: time
    hora_fim: time
    tipo: str
    vagas: int
    vagas_livres: int


class DashboardRead(BaseModel):
    inicio: date
    fim: date
    setor_id: int | None
    turnos_programados: int
    pessoas_escaladas: int
    vagas: VagasIndicador
    serie_por_dia: list[VagasPorDia]
    turnos_com_vaga: list[TurnoComVaga]
