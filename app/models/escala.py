from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import agora

if TYPE_CHECKING:
    from app.models.setor import Setor
    from app.models.turno import Turno

STATUS_ESCALA = ("rascunho", "publicada", "encerrada")


class Escala(Base):
    __tablename__ = "escalas"
    __table_args__ = (CheckConstraint("data_fim >= data_inicio", name="ck_escala_periodo"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(160))
    setor_id: Mapped[int] = mapped_column(ForeignKey("setores.id"))
    data_inicio: Mapped[date]
    data_fim: Mapped[date]
    status: Mapped[str] = mapped_column(String(20), default="rascunho")
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    setor: Mapped[Setor] = relationship(back_populates="escalas")
    turnos: Mapped[list[Turno]] = relationship(
        back_populates="escala",
        cascade="all, delete-orphan",
        order_by="(Turno.data, Turno.hora_inicio)",
    )
