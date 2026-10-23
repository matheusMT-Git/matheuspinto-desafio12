"""CA2 – atribuir turno respeitando vagas e horários."""

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Servidor, Turno


def id_turno(db: Session, numero: int) -> int:
    """Id do turno Tnn do seed (os turnos são criados na ordem T01..T12)."""
    return db.scalars(select(Turno.id).order_by(Turno.id)).all()[numero - 1]


def id_servidor(db: Session, matricula: str) -> int:
    return db.scalars(select(Servidor.id).where(Servidor.matricula == matricula)).one()


def atribuir(client: TestClient, db: Session, turno: int, matricula: str):
    return client.post(
        f"/api/v1/turnos/{id_turno(db, turno)}/atribuicoes",
        json={"servidor_id": id_servidor(db, matricula)},
    )


def vagas_livres(client: TestClient, db: Session, turno: int) -> int:
    escalas = (
        client.get("/api/v1/escalas/1").json()["turnos"]
        + client.get("/api/v1/escalas/2").json()["turnos"]
    )
    return next(t["vagas_livres"] for t in escalas if t["id"] == id_turno(db, turno))


# --- caso feliz -------------------------------------------------------------------------


def test_atribui_servidor_e_vagas_livres_diminuem_em_1(client: TestClient, db: Session) -> None:
    assert vagas_livres(client, db, 3) == 1  # T03: S01, S02 de 3 vagas

    resposta = atribuir(client, db, 3, "S04")

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "confirmada"
    assert vagas_livres(client, db, 3) == 0


# --- os 3 casos de recusa do seed -------------------------------------------------------


def test_turno_lotado_devolve_409(client: TestClient, db: Session) -> None:
    resposta = atribuir(client, db, 1, "S06")  # T01 tem 3 de 3 vagas
    assert resposta.status_code == 409
    assert resposta.json() == {"detail": "Turno sem vagas."}


def test_choque_de_horario_devolve_409(client: TestClient, db: Session) -> None:
    resposta = atribuir(client, db, 1, "S07")  # S07 está em T08 (08:00–14:00) no mesmo dia
    assert resposta.status_code == 409
    assert "Choque de horário" in resposta.json()["detail"]
    assert "26/10/2026" in resposta.json()["detail"]


def test_servidor_inativo_devolve_422(client: TestClient, db: Session) -> None:
    resposta = atribuir(client, db, 9, "S10")  # S10 está afastado
    assert resposta.status_code == 422
    assert resposta.json() == {"detail": "Servidor inativo não pode ser escalado."}


# --- outras regras ----------------------------------------------------------------------


def test_recusa_nao_altera_as_vagas(client: TestClient, db: Session) -> None:
    atribuir(client, db, 9, "S10")
    atribuir(client, db, 1, "S06")
    assert vagas_livres(client, db, 9) == 1
    assert vagas_livres(client, db, 1) == 0


def test_servidor_ja_atribuido_ao_turno_devolve_409(client: TestClient, db: Session) -> None:
    resposta = atribuir(client, db, 3, "S01")
    assert resposta.status_code == 409
    assert "já está atribuído" in resposta.json()["detail"]


def test_turnos_em_sequencia_sem_sobreposicao_sao_aceitos(client: TestClient, db: Session) -> None:
    # S02 está em T01 (07–13) e em T03 (ter); T02 (13–19, seg) começa quando T01 termina.
    assert atribuir(client, db, 2, "S02").status_code == 201


def test_servidor_ou_turno_inexistente_devolve_404(client: TestClient, db: Session) -> None:
    assert client.post("/api/v1/turnos/999/atribuicoes", json={"servidor_id": 1}).status_code == 404
    turno = id_turno(db, 3)
    assert (
        client.post(f"/api/v1/turnos/{turno}/atribuicoes", json={"servidor_id": 999}).status_code
        == 404
    )


def test_turno_noturno_que_vira_o_dia_conflita_com_turno_da_madrugada(
    client: TestClient, db: Session
) -> None:
    noite = client.post(
        "/api/v1/escalas/1/turnos",
        json={
            "data": "2026-10-28",
            "hora_inicio": "22:00",
            "hora_fim": "06:00",
            "tipo": "noite",
            "vagas": 2,
        },
    ).json()
    madrugada = client.post(
        "/api/v1/escalas/1/turnos",
        json={
            "data": "2026-10-29",
            "hora_inicio": "05:00",
            "hora_fim": "09:00",
            "tipo": "manhã",
            "vagas": 2,
        },
    ).json()
    servidor = id_servidor(db, "S04")

    assert (
        client.post(
            f"/api/v1/turnos/{noite['id']}/atribuicoes", json={"servidor_id": servidor}
        ).status_code
        == 201
    )
    choque = client.post(
        f"/api/v1/turnos/{madrugada['id']}/atribuicoes", json={"servidor_id": servidor}
    )
    assert choque.status_code == 409
    assert "Choque de horário" in choque.json()["detail"]


def test_escala_encerrada_nao_aceita_atribuicao(client: TestClient, db: Session) -> None:
    client.patch("/api/v1/escalas/1/status", json={"status": "encerrada"})
    resposta = atribuir(client, db, 3, "S04")
    assert resposta.status_code == 409


# --- cancelamento -----------------------------------------------------------------------


def test_cancela_atribuicao_e_libera_a_vaga(client: TestClient, db: Session) -> None:
    atribuicao = atribuir(client, db, 3, "S04").json()

    resposta = client.delete(f"/api/v1/atribuicoes/{atribuicao['id']}")

    assert resposta.status_code == 204
    assert vagas_livres(client, db, 3) == 1
    detalhe = client.get("/api/v1/escalas/1").json()["turnos"][2]
    assert next(a for a in detalhe["atribuicoes"] if a["id"] == atribuicao["id"])["status"] == (
        "cancelada"
    )


def test_reatribui_servidor_cuja_atribuicao_foi_cancelada(client: TestClient, db: Session) -> None:
    primeira = atribuir(client, db, 3, "S04").json()
    client.delete(f"/api/v1/atribuicoes/{primeira['id']}")

    segunda = atribuir(client, db, 3, "S04")

    assert segunda.status_code == 201
    assert segunda.json()["id"] == primeira["id"]
    assert vagas_livres(client, db, 3) == 0


def test_cancelar_atribuicao_inexistente_devolve_404(client: TestClient) -> None:
    assert client.delete("/api/v1/atribuicoes/999").status_code == 404


# --- servidores -------------------------------------------------------------------------


def test_lista_servidores_com_filtros(client: TestClient) -> None:
    todos = client.get("/api/v1/servidores").json()
    assert len(todos) == 10
    assert [s["matricula"] for s in client.get("/api/v1/servidores?ativo=false").json()] == ["S10"]
    pro_ativos = client.get("/api/v1/servidores?setor_id=2&ativo=true").json()
    assert sorted(s["matricula"] for s in pro_ativos) == ["S07", "S08", "S09"]


# --- telas web --------------------------------------------------------------------------


def test_tela_da_escala_mostra_grade_com_vagas_e_seletor(client: TestClient) -> None:
    pagina = client.get("/escalas/1")
    assert pagina.status_code == 200
    assert "0 livre(s) de 3" in pagina.text
    assert "S06 – Rafael Almeida" in pagina.text
    assert "S10" not in pagina.text  # inativo não aparece no seletor


def test_atribuir_pela_tela_troca_o_cartao_do_turno(client: TestClient, db: Session) -> None:
    turno = id_turno(db, 3)
    resposta = client.post(
        f"/escalas/turnos/{turno}/atribuir", data={"servidor_id": id_servidor(db, "S04")}
    )
    assert resposta.status_code == 200
    assert "0 livre(s) de 3" in resposta.text
    assert "João Pedro Martins" in resposta.text


def test_atribuir_pela_tela_mostra_erro_de_regra(client: TestClient, db: Session) -> None:
    turno = id_turno(db, 1)
    lotado = client.post(
        f"/escalas/turnos/{turno}/atribuir", data={"servidor_id": id_servidor(db, "S06")}
    )
    assert lotado.status_code == 409
    assert "Turno sem vagas." in lotado.text

    sem_selecao = client.post(f"/escalas/turnos/{turno}/atribuir", data={})
    assert sem_selecao.status_code == 422
    assert "Selecione um servidor." in sem_selecao.text


def test_cancelar_pela_tela_libera_a_vaga(client: TestClient, db: Session) -> None:
    atribuicao = atribuir(client, db, 3, "S04").json()
    resposta = client.post(f"/escalas/atribuicoes/{atribuicao['id']}/cancelar")
    assert resposta.status_code == 200
    assert "1 livre(s) de 3" in resposta.text
    assert "(S04)" not in resposta.text  # só aparece em quem está escalado
