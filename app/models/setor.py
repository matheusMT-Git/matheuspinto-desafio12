from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.escala import Escala
    from app.models.servidor import Servidor


class Setor(Base):
    __tablename__ = "setores"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), unique=True)
    sigla: Mapped[str] = mapped_column(String(10))

    servidores: Mapped[list[Servidor]] = relationship(back_populates="setor")
    escalas: Mapped[list[Escala]] = relationship(back_populates="setor")
