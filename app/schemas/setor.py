from pydantic import BaseModel, ConfigDict


class SetorCreate(BaseModel):
    nome: str
    sigla: str


class SetorUpdate(BaseModel):
    nome: str | None = None
    sigla: str | None = None


class SetorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    sigla: str
