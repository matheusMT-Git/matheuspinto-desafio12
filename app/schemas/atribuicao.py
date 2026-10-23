from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

StatusAtribuicao = Literal["confirmada", "cancelada"]


class AtribuicaoCreate(BaseModel):
    servidor_id: int


class AtribuicaoUpdate(BaseModel):
    status: StatusAtribuicao


class AtribuicaoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    turno_id: int
    servidor_id: int
    status: StatusAtribuicao
    criado_em: datetime
