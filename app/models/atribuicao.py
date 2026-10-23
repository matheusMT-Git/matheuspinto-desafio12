from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.utils import agora

if TYPE_CHECKING:
    from app.models.servidor import Servidor
    from app.models.turno import Turno

STATUS_ATRIBUICAO = ("confirmada", "cancelada")


class Atribuicao(Base):
    __tablename__ = "atribuicoes"
    __table_args__ = (UniqueConstraint("turno_id", "servidor_id", name="uq_atribuicao_par"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    turno_id: Mapped[int] = mapped_column(ForeignKey("turnos.id"))
    servidor_id: Mapped[int] = mapped_column(ForeignKey("servidores.id"))
    status: Mapped[str] = mapped_column(String(20), default="confirmada")
    criado_em: Mapped[datetime] = mapped_column(default=agora)

    turno: Mapped[Turno] = relationship(back_populates="atribuicoes")
    servidor: Mapped[Servidor] = relationship(back_populates="atribuicoes")
