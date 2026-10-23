from datetime import date, time
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.atribuicao import AtribuicaoRead

TipoTurno = Literal["manhã", "tarde", "noite", "plantão 12h"]


class TurnoCreate(BaseModel):
    data: date
    hora_inicio: time
    hora_fim: time
    tipo: TipoTurno
    vagas: int


class TurnoUpdate(BaseModel):
    data: date | None = None
    hora_inicio: time | None = None
    hora_fim: time | None = None
    tipo: TipoTurno | None = None
    vagas: int | None = None


class TurnoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    escala_id: int
    data: date
    hora_inicio: time
    hora_fim: time
    tipo: TipoTurno
    vagas: int
    vagas_livres: int


class TurnoDetalhe(TurnoRead):
    atribuicoes: list[AtribuicaoRead] = []
