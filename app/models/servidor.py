from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.atribuicao import Atribuicao
    from app.models.setor import Setor


class Servidor(Base):
    __tablename__ = "servidores"

    id: Mapped[int] = mapped_column(primary_key=True)
    matricula: Mapped[str] = mapped_column(String(20), unique=True)
    nome: Mapped[str] = mapped_column(String(120))
    cargo: Mapped[str] = mapped_column(String(120))
    setor_id: Mapped[int] = mapped_column(ForeignKey("setores.id"))
    carga_horaria_semanal: Mapped[int]
    ativo: Mapped[bool] = mapped_column(default=True)

    setor: Mapped[Setor] = relationship(back_populates="servidores")
    atribuicoes: Mapped[list[Atribuicao]] = relationship(back_populates="servidor")
