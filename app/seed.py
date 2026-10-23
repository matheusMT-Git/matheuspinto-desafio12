"""Dados fictícios: `python -m app.seed` recria o banco (migrações + carga)."""

from datetime import date, time
from pathlib import Path

from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import command
from app.database import SessionLocal, engine
from app.models import Atribuicao, Escala, Servidor, Setor, Turno

RAIZ = Path(__file__).resolve().parent.parent

SETORES = [
    ("Central de Atendimento ao Cidadão", "CAC"),
    ("Protocolo Geral", "PRO"),
]

# (matrícula, nome, cargo, sigla do setor, carga semanal, ativo)
SERVIDORES = [
    ("S01", "Ana Paula Ribeiro", "Técnica Administrativa", "CAC", 40, True),
    ("S02", "Carlos Eduardo Lima", "Agente de Atendimento", "CAC", 40, True),
    ("S03", "Fernanda Souza", "Agente de Atendimento", "CAC", 30, True),
    ("S04", "João Pedro Martins", "Técnico Administrativo", "CAC", 40, True),
    ("S05", "Mariana Costa", "Agente de Atendimento", "CAC", 30, True),
    ("S06", "Rafael Almeida", "Supervisor de Atendimento", "CAC", 40, True),
    ("S07", "Beatriz Nogueira", "Assistente de Protocolo", "PRO", 30, True),
    ("S08", "Lucas Ferreira", "Assistente de Protocolo", "PRO", 30, True),
    ("S09", "Patrícia Gomes", "Analista Administrativa", "PRO", 40, True),
    ("S10", "Roberto Dias", "Assistente de Protocolo", "PRO", 30, False),
]

# (nome, sigla do setor, início, fim, status)
ESCALAS = [
    ("Atendimento CAC – Semana 44", "CAC", date(2026, 10, 26), date(2026, 11, 1), "publicada"),
    ("Protocolo – Semana 44", "PRO", date(2026, 10, 26), date(2026, 10, 30), "rascunho"),
]

# (escala, data, início, fim, tipo, vagas, matrículas confirmadas, matrículas canceladas)
TURNOS = [
    (1, date(2026, 10, 26), time(7), time(13), "manhã", 3, ["S01", "S02", "S03"], []),
    (1, date(2026, 10, 26), time(13), time(19), "tarde", 3, ["S04", "S05"], []),
    (1, date(2026, 10, 27), time(7), time(13), "manhã", 3, ["S01", "S02"], []),
    (1, date(2026, 10, 27), time(13), time(19), "tarde", 3, ["S03", "S04", "S06"], []),
    (1, date(2026, 10, 28), time(7), time(13), "manhã", 3, ["S05", "S06"], []),
    (1, date(2026, 10, 28), time(13), time(19), "tarde", 3, ["S01"], ["S03"]),
    (1, date(2026, 10, 31), time(8), time(20), "plantão 12h", 2, ["S02"], []),
    (2, date(2026, 10, 26), time(8), time(14), "manhã", 2, ["S07", "S08"], []),
    (2, date(2026, 10, 27), time(8), time(14), "manhã", 2, ["S07"], []),
    (2, date(2026, 10, 28), time(8), time(14), "manhã", 2, ["S08"], []),
    (2, date(2026, 10, 29), time(8), time(14), "manhã", 2, ["S07", "S08"], []),
    (2, date(2026, 10, 30), time(8), time(14), "manhã", 3, ["S07", "S08"], []),
]


def carregar_seed(db: Session) -> None:
    """Insere os dados fictícios em um banco com o esquema já criado e vazio."""
    setores = {sigla: Setor(nome=nome, sigla=sigla) for nome, sigla in SETORES}
    db.add_all(setores.values())

    servidores = {
        matricula: Servidor(
            matricula=matricula,
            nome=nome,
            cargo=cargo,
            setor=setores[sigla],
            carga_horaria_semanal=carga,
            ativo=ativo,
        )
        for matricula, nome, cargo, sigla, carga, ativo in SERVIDORES
    }
    db.add_all(servidores.values())

    escalas = [
        Escala(nome=nome, setor=setores[sigla], data_inicio=ini, data_fim=fim, status=status)
        for nome, sigla, ini, fim, status in ESCALAS
    ]
    db.add_all(escalas)

    for num_escala, data, ini, fim, tipo, vagas, confirmadas, canceladas in TURNOS:
        turno = Turno(
            escala=escalas[num_escala - 1],
            data=data,
            hora_inicio=ini,
            hora_fim=fim,
            tipo=tipo,
            vagas=vagas,
        )
        db.add(turno)
        for matricula in confirmadas:
            db.add(Atribuicao(turno=turno, servidor=servidores[matricula], status="confirmada"))
        for matricula in canceladas:
            db.add(Atribuicao(turno=turno, servidor=servidores[matricula], status="cancelada"))
    db.commit()


def recriar_banco() -> None:
    """Apaga tudo, aplica as migrações do Alembic e carrega o seed."""
    with engine.begin() as conexao:
        nomes = conexao.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        ).scalars()
        tabelas = list(nomes)
        conexao.execute(text("PRAGMA foreign_keys=OFF"))
        for tabela in tabelas:
            conexao.execute(text(f'DROP TABLE IF EXISTS "{tabela}"'))
        conexao.execute(text("PRAGMA foreign_keys=ON"))

    config = Config(str(RAIZ / "alembic.ini"))
    config.set_main_option("script_location", str(RAIZ / "alembic"))
    command.upgrade(config, "head")

    with SessionLocal() as db:
        carregar_seed(db)


if __name__ == "__main__":
    recriar_banco()
    print("Banco recriado com os dados fictícios.")
