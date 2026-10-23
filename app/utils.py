from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def agora() -> datetime:
    """Data e hora atuais em America/Sao_Paulo, sem informação de fuso (para o SQLite)."""
    return datetime.now(FUSO).replace(tzinfo=None)


def hoje() -> date:
    return agora().date()


def semana_de(referencia: date) -> tuple[date, date]:
    """Segunda e domingo da semana que contém a data."""
    segunda = referencia - timedelta(days=referencia.weekday())
    return segunda, segunda + timedelta(days=6)
