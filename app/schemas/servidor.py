from pydantic import BaseModel, ConfigDict


class ServidorCreate(BaseModel):
    matricula: str
    nome: str
    cargo: str
    setor_id: int
    carga_horaria_semanal: int
    ativo: bool = True


class ServidorUpdate(BaseModel):
    nome: str | None = None
    cargo: str | None = None
    setor_id: int | None = None
    carga_horaria_semanal: int | None = None
    ativo: bool | None = None


class ServidorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    matricula: str
    nome: str
    cargo: str
    setor_id: int
    carga_horaria_semanal: int
    ativo: bool
