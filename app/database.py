import os
import tempfile
from collections.abc import Iterator
from pathlib import Path
from sqlite3 import Connection as SQLiteConnection

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# No Vercel o disco do projeto é somente leitura; só o diretório temporário é gravável.
NO_VERCEL = bool(os.environ.get("VERCEL"))
DATABASE_URL = (
    f"sqlite:///{(Path(tempfile.gettempdir()) / 'escalas.db').as_posix()}"
    if NO_VERCEL
    else "sqlite:///./escalas.db"
)


class Base(DeclarativeBase):
    pass


@event.listens_for(Engine, "connect")
def _ativar_chaves_estrangeiras(conexao: object, _registro: object) -> None:
    if isinstance(conexao, SQLiteConnection):
        cursor = conexao.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
