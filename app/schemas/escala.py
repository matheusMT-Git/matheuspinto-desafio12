from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.turno import TurnoCreate, TurnoDetalhe

StatusEscala = Literal["rascunho", "publicada", "encerrada"]


class EscalaCreate(BaseModel):
    nome: str
    setor_id: int
    data_inicio: date
    data_fim: date
    turnos: list[TurnoCreate] = []


class EscalaUpdate(BaseModel):
    nome: str | None = None
    data_inicio: date | None = None
    data_fim: date | None = None


class EscalaStatusUpdate(BaseModel):
    status: StatusEscala


class EscalaRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    setor_id: int
    data_inicio: date
    data_fim: date
    status: StatusEscala
    criado_em: datetime


class EscalaDetalhe(EscalaRead):
    turnos: list[TurnoDetalhe] = []
