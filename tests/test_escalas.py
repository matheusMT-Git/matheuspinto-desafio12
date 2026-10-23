"""CA1 – cadastrar escala com turnos válidos."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Atribuicao, Escala, Servidor, Turno

TURNO_OK = {
    "data": "2026-11-02",
    "hora_inicio": "08:00",
    "hora_fim": "14:00",
    "tipo": "manhã",
    "vagas": 2,
}


def escala_payload(**extra: object) -> dict:
    return {
        "nome": "Atendimento CAC – Semana 45",
        "setor_id": 1,
        "data_inicio": "2026-11-02",
        "data_fim": "2026-11-08",
        **extra,
    }


def total_escalas(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Escala)) or 0


def total_turnos(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(Turno)) or 0


# --- seed -------------------------------------------------------------------------------


def test_seed_bate_com_a_especificacao(db: Session) -> None:
    confirmadas = db.scalar(
        select(func.count()).select_from(Atribuicao).where(Atribuicao.status == "confirmada")
    )
    assert total_escalas(db) == 2
    assert total_turnos(db) == 12
    assert confirmadas == 22
    assert db.scalar(select(func.count()).select_from(Atribuicao)) == 23
    assert db.scalar(select(func.count()).select_from(Servidor)) == 10
    assert sum(t.vagas_livres for t in db.scalars(select(Turno))) == 9


# --- API: cadastro ----------------------------------------------------------------------


def test_cadastra_escala_com_turnos_como_rascunho_e_lista(client: TestClient) -> None:
    resposta = client.post("/api/v1/escalas", json=escala_payload(turnos=[TURNO_OK]))

    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["status"] == "rascunho"
    assert len(corpo["turnos"]) == 1
    assert corpo["turnos"][0]["vagas_livres"] == 2

    lista = client.get("/api/v1/escalas").json()
    assert corpo["id"] in [e["id"] for e in lista]


def test_cadastra_escala_sem_turnos(client: TestClient) -> None:
    resposta = client.post("/api/v1/escalas", json=escala_payload())
    assert resposta.status_code == 201
    assert resposta.json()["turnos"] == []


def test_periodo_de_31_dias_e_aceito_e_de_32_e_recusado(client: TestClient) -> None:
    ok = client.post(
        "/api/v1/escalas", json=escala_payload(data_inicio="2026-11-01", data_fim="2026-12-01")
    )
    assert ok.status_code == 201

    longo = client.post(
        "/api/v1/escalas", json=escala_payload(data_inicio="2026-11-01", data_fim="2026-12-02")
    )
    assert longo.status_code == 422
    assert "31 dias" in longo.json()["detail"]


def test_data_final_anterior_a_inicial_e_bloqueada(client: TestClient, db: Session) -> None:
    antes = total_escalas(db)
    resposta = client.post(
        "/api/v1/escalas", json=escala_payload(data_inicio="2026-11-08", data_fim="2026-11-02")
    )

    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "A data final não pode ser anterior à data inicial."}
    assert total_escalas(db) == antes


def test_turno_fora_do_periodo_bloqueia_e_nada_e_gravado(client: TestClient, db: Session) -> None:
    escalas_antes, turnos_antes = total_escalas(db), total_turnos(db)
    turno_fora = {**TURNO_OK, "data": "2026-11-09"}

    resposta = client.post("/api/v1/escalas", json=escala_payload(turnos=[TURNO_OK, turno_fora]))

    assert resposta.status_code == 422
    assert "fora do período" in resposta.json()["detail"]
    assert total_escalas(db) == escalas_antes
    assert total_turnos(db) == turnos_antes


def test_turno_com_zero_vagas_e_recusado(client: TestClient) -> None:
    resposta = client.post(
        "/api/v1/escalas", json=escala_payload(turnos=[{**TURNO_OK, "vagas": 0}])
    )
    assert resposta.status_code == 422
    assert resposta.json()["detail"] == "O turno deve ter ao menos 1 vaga."


def test_horario_final_deve_ser_maior_exceto_turno_noturno(client: TestClient) -> None:
    invertido = {**TURNO_OK, "hora_inicio": "14:00", "hora_fim": "08:00"}
    recusado = client.post("/api/v1/escalas", json=escala_payload(turnos=[invertido]))
    assert recusado.status_code == 422

    noturno = {**TURNO_OK, "tipo": "noite", "hora_inicio": "19:00", "hora_fim": "07:00"}
    aceito = client.post("/api/v1/escalas", json=escala_payload(turnos=[noturno]))
    assert aceito.status_code == 201


def test_setor_inexistente_e_nome_vazio_sao_recusados(client: TestClient) -> None:
    assert client.post("/api/v1/escalas", json=escala_payload(setor_id=99)).status_code == 422
    assert client.post("/api/v1/escalas", json=escala_payload(nome="  ")).status_code == 422


def test_campo_obrigatorio_ausente_devolve_422_em_portugues(client: TestClient) -> None:
    resposta = client.post("/api/v1/escalas", json={"nome": "X"})
    assert resposta.status_code == 422
    assert resposta.json()["detail"].startswith("Preencha corretamente")


# --- API: turnos, listagem, detalhe e status ---------------------------------------------


def test_cria_turno_em_escala_existente(client: TestClient) -> None:
    resposta = client.post("/api/v1/escalas/2/turnos", json={**TURNO_OK, "data": "2026-10-30"})
    assert resposta.status_code == 201
    assert resposta.json()["vagas_livres"] == 2


def test_turno_fora_do_periodo_em_escala_existente_e_recusado(
    client: TestClient, db: Session
) -> None:
    antes = total_turnos(db)
    resposta = client.post("/api/v1/escalas/2/turnos", json={**TURNO_OK, "data": "2026-10-31"})
    assert resposta.status_code == 422
    assert total_turnos(db) == antes


def test_filtra_escalas_por_setor_e_status(client: TestClient) -> None:
    assert [e["id"] for e in client.get("/api/v1/escalas?setor_id=2").json()] == [2]
    assert [e["id"] for e in client.get("/api/v1/escalas?status=publicada").json()] == [1]
    assert client.get("/api/v1/escalas?status=invalido").status_code == 422


def test_detalha_escala_com_turnos_e_atribuicoes(client: TestClient) -> None:
    corpo = client.get("/api/v1/escalas/1").json()
    assert len(corpo["turnos"]) == 7
    primeiro = corpo["turnos"][0]
    assert primeiro["vagas"] == 3
    assert primeiro["vagas_livres"] == 0
    assert len(primeiro["atribuicoes"]) == 3
    # T06 tem uma atribuição cancelada que não ocupa vaga
    t06 = corpo["turnos"][5]
    assert len(t06["atribuicoes"]) == 2
    assert t06["vagas_livres"] == 2


def test_escala_inexistente_devolve_404(client: TestClient) -> None:
    resposta = client.get("/api/v1/escalas/999")
    assert resposta.status_code == 404
    assert resposta.json() == {"detail": "Escala não encontrada."}


def test_publica_escala_em_rascunho(client: TestClient) -> None:
    resposta = client.patch("/api/v1/escalas/2/status", json={"status": "publicada"})
    assert resposta.status_code == 200
    assert resposta.json()["status"] == "publicada"


def test_transicao_de_status_invalida_devolve_409(client: TestClient) -> None:
    resposta = client.patch("/api/v1/escalas/1/status", json={"status": "rascunho"})
    assert resposta.status_code == 409


# --- Telas web --------------------------------------------------------------------------


def test_tela_lista_escalas_do_seed(client: TestClient) -> None:
    resposta = client.get("/escalas")
    assert resposta.status_code == 200
    assert "Atendimento CAC – Semana 44" in resposta.text
    assert "26/10/2026 a 01/11/2026" in resposta.text


def test_formulario_cadastra_escala_com_turno_e_ela_aparece_na_lista(
    client: TestClient, db: Session
) -> None:
    resposta = client.post(
        "/escalas",
        data={
            "nome": "Escala pela tela",
            "setor_id": "1",
            "data_inicio": "2026-11-02",
            "data_fim": "2026-11-08",
            "turno_data": ["2026-11-03"],
            "turno_inicio": ["08:00"],
            "turno_fim": ["12:00"],
            "turno_tipo": ["manhã"],
            "turno_vagas": ["2"],
        },
    )
    assert resposta.status_code == 200
    assert "Escala pela tela" in resposta.text
    assert "rascunho" in resposta.text
    assert total_escalas(db) == 3
    assert total_turnos(db) == 13


def test_formulario_com_turno_fora_do_periodo_mostra_mensagem_e_nao_grava(
    client: TestClient, db: Session
) -> None:
    resposta = client.post(
        "/escalas",
        data={
            "nome": "Escala inválida",
            "setor_id": "1",
            "data_inicio": "2026-11-02",
            "data_fim": "2026-11-08",
            "turno_data": ["2026-12-01"],
            "turno_inicio": ["08:00"],
            "turno_fim": ["12:00"],
            "turno_tipo": ["manhã"],
            "turno_vagas": ["1"],
        },
    )
    assert resposta.status_code == 422
    assert "fora do período" in resposta.text
    assert total_escalas(db) == 2


def test_formulario_com_data_final_anterior_mostra_mensagem(
    client: TestClient, db: Session
) -> None:
    resposta = client.post(
        "/escalas",
        data={
            "nome": "Escala inválida",
            "setor_id": "1",
            "data_inicio": "2026-11-08",
            "data_fim": "2026-11-02",
        },
    )
    assert resposta.status_code == 422
    assert "data final não pode ser anterior" in resposta.text
    assert total_escalas(db) == 2


def test_tela_de_detalhe_e_inclusao_de_turno(client: TestClient) -> None:
    pagina = client.get("/escalas/2")
    assert pagina.status_code == 200
    assert "Protocolo – Semana 44" in pagina.text

    resposta = client.post(
        "/escalas/2/turnos",
        data={
            "data": "2026-10-30",
            "hora_inicio": "14:00",
            "hora_fim": "18:00",
            "tipo": "tarde",
            "vagas": "1",
        },
    )
    assert resposta.status_code == 200
    assert "14:00–18:00" in resposta.text


def test_tela_de_detalhe_inexistente_devolve_404(client: TestClient) -> None:
    assert client.get("/escalas/999").status_code == 404
