from __future__ import annotations

from datetime import date, time
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.atribuicao import Atribuicao
    from app.models.escala import Escala

TIPOS_TURNO = ("manhã", "tarde", "noite", "plantão 12h")


class Turno(Base):
    __tablename__ = "turnos"
    __table_args__ = (CheckConstraint("vagas >= 1", name="ck_turno_vagas"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    escala_id: Mapped[int] = mapped_column(ForeignKey("escalas.id"))
    data: Mapped[date]
    hora_inicio: Mapped[time]
    hora_fim: Mapped[time]
    tipo: Mapped[str] = mapped_column(String(20))
    vagas: Mapped[int]

    escala: Mapped[Escala] = relationship(back_populates="turnos")
    atribuicoes: Mapped[list[Atribuicao]] = relationship(
        back_populates="turno", cascade="all, delete-orphan", order_by="Atribuicao.id"
    )

    @property
    def vagas_livres(self) -> int:
        confirmadas = sum(1 for a in self.atribuicoes if a.status == "confirmada")
        return self.vagas - confirmadas
