from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.database import Base, get_db
from app.main import app
from app.seed import carregar_seed


@pytest.fixture()
def db() -> Iterator[Session]:
    """Banco SQLite em memória, recriado e populado com o seed a cada teste."""
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    carregar_seed(sessao)
    yield sessao
    sessao.close()
    engine.dispose()


@pytest.fixture()
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as cliente:
        yield cliente
    app.dependency_overrides.clear()
