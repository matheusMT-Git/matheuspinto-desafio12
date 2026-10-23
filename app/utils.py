from datetime import datetime
from zoneinfo import ZoneInfo

FUSO = ZoneInfo("America/Sao_Paulo")


def agora() -> datetime:
    """Data e hora atuais em America/Sao_Paulo, sem informação de fuso (para o SQLite)."""
    return datetime.now(FUSO).replace(tzinfo=None)
