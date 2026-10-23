"""CA3 – consultar agenda e ver indicadores consistentes."""

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Servidor, Turno

SEMANA = "inicio=2026-10-26&fim=2026-11-01"

# Tabela do CLAUDE.md: turno -> (servidores escalados, vagas livres)
ESPERADO = {
    1: (["S01", "S02", "S03"], 0),
    2: (["S04", "S05"], 1),
    3: (["S01", "S02"], 1),
    4: (["S03", "S04", "S06"], 0),
    5: (["S05", "S06"], 1),
    6: (["S01"], 2),
    7: (["S02"], 1),
    8: (["S07", "S08"], 0),
    9: (["S07"], 1),
    10: (["S08"], 1),
    11: (["S07", "S08"], 0),
    12: (["S07", "S08"], 1),
}


def ids_turnos(db: Session) -> dict[int, int]:
    return {n: i for n, i in enumerate(db.scalars(select(Turno.id).order_by(Turno.id)), start=1)}


def id_servidor(db: Session, matricula: str) -> int:
    return db.scalars(select(Servidor.id).where(Servidor.matricula == matricula)).one()


def agenda(client: TestClient, consulta: str) -> list[dict]:
    resposta = client.get(f"/api/v1/agenda?{consulta}")
    assert resposta.status_code == 200
    return resposta.json()


def dashboard(client: TestClient, consulta: str = SEMANA) -> dict:
    resposta = client.get(f"/api/v1/dashboard?{consulta}")
    assert resposta.status_code == 200
    return resposta.json()


# --- agenda -----------------------------------------------------------------------------


def test_agenda_da_semana_lista_os_12_turnos_com_servidores_e_vagas(
    client: TestClient, db: Session
) -> None:
    turnos = agenda(client, SEMANA)
    ids = ids_turnos(db)

    assert len(turnos) == 12
    por_id = {t["id"]: t for t in turnos}
    for numero, (matriculas, livres) in ESPERADO.items():
        turno = por_id[ids[numero]]
        assert sorted(s["matricula"] for s in turno["servidores"]) == matriculas, f"T{numero:02d}"
        assert turno["vagas_livres"] == livres, f"T{numero:02d}"


def test_agenda_vem_ordenada_por_data_e_hora(client: TestClient) -> None:
    turnos = agenda(client, SEMANA)
    chaves = [(t["data"], t["hora_inicio"]) for t in turnos]
    assert chaves == sorted(chaves)


def test_agenda_do_servidor_s01(client: TestClient, db: Session) -> None:
    servidor = id_servidor(db, "S01")
    turnos = agenda(client, f"{SEMANA}&servidor_id={servidor}")
    ids = ids_turnos(db)
    assert [t["id"] for t in turnos] == [ids[1], ids[3], ids[6]]


def test_agenda_do_setor_pro(client: TestClient, db: Session) -> None:
    turnos = agenda(client, "inicio=2026-10-26&fim=2026-10-30&setor_id=2")
    ids = ids_turnos(db)
    assert sorted(t["id"] for t in turnos) == [ids[n] for n in range(8, 13)]
    assert sum(len(t["servidores"]) for t in turnos) == 8
    assert sum(t["vagas_livres"] for t in turnos) == 3


def test_agenda_de_servidor_sem_turno_na_semana_e_vazia(client: TestClient, db: Session) -> None:
    assert agenda(client, f"{SEMANA}&servidor_id={id_servidor(db, 'S09')}") == []


def test_agenda_nao_lista_atribuicao_cancelada(client: TestClient, db: Session) -> None:
    # S03 teve a atribuição ao T06 cancelada: não aparece na agenda dele
    assert [t["id"] for t in agenda(client, f"{SEMANA}&servidor_id={id_servidor(db, 'S03')}")] == [
        ids_turnos(db)[1],
        ids_turnos(db)[4],
    ]


def test_agenda_valida_o_periodo(client: TestClient) -> None:
    longo = client.get("/api/v1/agenda?inicio=2026-10-01&fim=2026-11-01")
    assert longo.status_code == 422
    assert "31 dias" in longo.json()["detail"]

    invertido = client.get("/api/v1/agenda?inicio=2026-11-01&fim=2026-10-26")
    assert invertido.status_code == 422

    assert client.get("/api/v1/agenda").status_code == 422  # período é obrigatório
    assert client.get("/api/v1/agenda?inicio=2026-10-01&fim=2026-10-31").status_code == 200


# --- dashboard --------------------------------------------------------------------------


def test_dashboard_da_semana_do_seed(client: TestClient) -> None:
    dados = dashboard(client)
    assert dados["turnos_programados"] == 12
    assert dados["pessoas_escaladas"] == 8
    assert dados["vagas"] == {
        "total": 31,
        "ocupadas": 22,
        "livres": 9,
        "ocupacao_percentual": 71,
        "nivel": "alerta",
    }


def test_serie_por_dia_soma_os_totais(client: TestClient) -> None:
    serie = dashboard(client)["serie_por_dia"]
    assert [d["data"] for d in serie][0] == "2026-10-26"
    assert len(serie) == 7
    assert sum(d["total"] for d in serie) == 31
    assert sum(d["ocupadas"] for d in serie) == 22
    assert sum(d["livres"] for d in serie) == 9
    segunda = serie[0]  # T01 + T02 + T08
    assert (segunda["total"], segunda["ocupadas"], segunda["livres"]) == (8, 7, 1)
    assert serie[3]["total"] == 2  # quinta: só T11


def test_dashboard_por_setor(client: TestClient) -> None:
    pro = dashboard(client, f"{SEMANA}&setor_id=2")
    assert pro["turnos_programados"] == 5
    assert pro["pessoas_escaladas"] == 2
    assert (pro["vagas"]["total"], pro["vagas"]["livres"]) == (11, 3)

    cac = dashboard(client, f"{SEMANA}&setor_id=1")
    assert cac["turnos_programados"] == 7
    assert cac["pessoas_escaladas"] == 6
    assert (cac["vagas"]["total"], cac["vagas"]["livres"], cac["vagas"]["ocupacao_percentual"]) == (
        20,
        6,
        70,
    )


def test_lista_de_turnos_com_vaga_aberta(client: TestClient, db: Session) -> None:
    abertos = dashboard(client)["turnos_com_vaga"]
    ids = ids_turnos(db)
    assert sorted(t["id"] for t in abertos) == sorted(ids[n] for n in (2, 3, 5, 6, 7, 9, 10, 12))
    assert sum(t["vagas_livres"] for t in abertos) == 9
    datas = [(t["data"], t["hora_inicio"]) for t in abertos]
    assert datas == sorted(datas)


def test_nivel_critico_quando_ocupacao_abaixo_de_50(client: TestClient) -> None:
    client.post(
        "/api/v1/escalas",
        json={
            "nome": "Sem ninguém",
            "setor_id": 1,
            "data_inicio": "2026-11-02",
            "data_fim": "2026-11-08",
            "turnos": [
                {
                    "data": "2026-11-02",
                    "hora_inicio": "08:00",
                    "hora_fim": "12:00",
                    "tipo": "manhã",
                    "vagas": 4,
                }
            ],
        },
    )
    vagas = dashboard(client, "inicio=2026-11-02&fim=2026-11-08")["vagas"]
    assert (vagas["ocupacao_percentual"], vagas["nivel"]) == (0, "critico")


def test_periodo_sem_turnos_zera_indicadores_sem_alerta(client: TestClient) -> None:
    dados = dashboard(client, "inicio=2027-01-04&fim=2027-01-10")
    assert dados["turnos_programados"] == 0
    assert dados["vagas"]["nivel"] == "normal"
    assert dados["turnos_com_vaga"] == []


def test_escala_encerrada_fica_fora_dos_indicadores(client: TestClient) -> None:
    client.patch("/api/v1/escalas/1/status", json={"status": "encerrada"})
    dados = dashboard(client)
    assert dados["turnos_programados"] == 5
    assert dados["vagas"]["total"] == 11


def test_dashboard_sem_periodo_usa_a_semana_corrente(client: TestClient) -> None:
    dados = client.get("/api/v1/dashboard").json()
    inicio, fim = date.fromisoformat(dados["inicio"]), date.fromisoformat(dados["fim"])
    assert inicio.weekday() == 0
    assert (fim - inicio).days == 6


def test_dashboard_valida_o_periodo(client: TestClient) -> None:
    assert client.get("/api/v1/dashboard?inicio=2026-10-01&fim=2026-12-01").status_code == 422


# --- consistência após mudanças ---------------------------------------------------------


def test_nova_atribuicao_e_cancelamento_refletem_em_agenda_e_dashboard(
    client: TestClient, db: Session
) -> None:
    t03 = ids_turnos(db)[3]
    s09 = id_servidor(db, "S09")

    criada = client.post(f"/api/v1/turnos/{t03}/atribuicoes", json={"servidor_id": s09})
    assert criada.status_code == 201

    dados = dashboard(client)
    assert dados["pessoas_escaladas"] == 9
    assert dados["vagas"]["livres"] == 8
    assert dados["vagas"]["ocupadas"] == 23
    turno = next(t for t in agenda(client, SEMANA) if t["id"] == t03)
    assert turno["vagas_livres"] == 0
    assert "S09" in [s["matricula"] for s in turno["servidores"]]
    assert len(agenda(client, f"{SEMANA}&servidor_id={s09}")) == 1

    assert client.delete(f"/api/v1/atribuicoes/{criada.json()['id']}").status_code == 204

    dados = dashboard(client)
    assert dados["pessoas_escaladas"] == 8
    assert dados["vagas"]["livres"] == 9
    assert agenda(client, f"{SEMANA}&servidor_id={s09}") == []


# --- telas ------------------------------------------------------------------------------


def test_tela_do_dashboard_mostra_os_cartoes_do_seed(client: TestClient) -> None:
    pagina = client.get(f"/?{SEMANA}")
    assert pagina.status_code == 200
    assert "Turnos programados" in pagina.text
    assert "9 <span>de 31</span>" in pagina.text
    assert "71% ocupado" in pagina.text
    assert "vagas-alerta" in pagina.text
    assert "Turnos com vaga aberta" in pagina.text
    assert "chart.js" in pagina.text


def test_tela_do_dashboard_com_periodo_invalido_mostra_mensagem(client: TestClient) -> None:
    pagina = client.get("/?inicio=2026-01-01&fim=2026-12-31")
    assert pagina.status_code == 422
    assert "não pode exceder 31 dias" in pagina.text


def test_tela_da_agenda_mostra_a_semana(client: TestClient) -> None:
    pagina = client.get("/agenda?semana=2026-10-28")
    assert pagina.status_code == 200
    assert "26/10/2026 a 01/11/2026" in pagina.text
    assert "12 turno(s)" in pagina.text
    assert "Ana Paula Ribeiro" in pagina.text
    assert "Domingo" in pagina.text


def test_tela_da_agenda_filtra_por_servidor_e_setor(client: TestClient, db: Session) -> None:
    servidor = id_servidor(db, "S01")
    pagina = client.get(f"/agenda?semana=2026-10-26&servidor_id={servidor}")
    assert "3 turno(s)" in pagina.text
    assert "5 turno(s)" in client.get("/agenda?semana=2026-10-26&setor_id=2").text
    assert "12 turno(s)" in client.get("/agenda?semana=2026-10-26&servidor_id=").text
