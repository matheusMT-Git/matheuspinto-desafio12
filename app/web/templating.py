from datetime import date, time
from pathlib import Path

from fastapi.templating import Jinja2Templates

from app.models.turno import TIPOS_TURNO

templates = Jinja2Templates(directory=Path(__file__).parent.parent / "templates")


def data_br(valor: date | None) -> str:
    return valor.strftime("%d/%m/%Y") if valor else ""


def hora_br(valor: time | None) -> str:
    return valor.strftime("%H:%M") if valor else ""


templates.env.filters["data_br"] = data_br
templates.env.filters["hora_br"] = hora_br
templates.env.globals["tipos_turno"] = TIPOS_TURNO
