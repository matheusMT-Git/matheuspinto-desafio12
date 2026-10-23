"""Cadastra dados fictícios pela interface e guarda prints em evidencias/playwright/.

Uso (com o servidor rodando em http://localhost:8000 e o banco já com o seed):
    python scripts/evidencias_playwright.py [url-base]

Usa o Chrome instalado (canal "chrome"), sem baixar navegador.
"""

import sys
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

BASE = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "http://localhost:8000"
PASTA = Path(__file__).resolve().parent.parent / "evidencias" / "playwright"

CAC, PRO = "1", "2"
# Ids dos servidores no seed: S01..S10 = 1..10
ESCALAS = [
    {
        "nome": "Atendimento CAC – Semana 45",
        "setor": CAC,
        "inicio": "2026-11-02",
        "fim": "2026-11-08",
        "turnos": [
            ("2026-11-02", "07:00", "13:00", "manhã", "3", [1, 2, 3]),
            ("2026-11-02", "13:00", "19:00", "tarde", "2", [4, 5]),
            ("2026-11-03", "19:00", "07:00", "noite", "1", [6]),
        ],
    },
    {
        "nome": "Protocolo – Semana 45",
        "setor": PRO,
        "inicio": "2026-11-02",
        "fim": "2026-11-06",
        "turnos": [
            ("2026-11-02", "08:00", "14:00", "manhã", "2", [7, 8]),
            ("2026-11-03", "08:00", "14:00", "manhã", "2", [9]),
        ],
    },
]

contador = 0


def print_tela(page: Page, nome: str) -> None:
    global contador
    contador += 1
    caminho = PASTA / f"{contador:02d}-{nome}.png"
    page.screenshot(path=str(caminho), full_page=True)
    print("evidência:", caminho.name)


def preencher_escala(page: Page, escala: dict) -> None:
    page.fill("input[name=nome]", escala["nome"])
    page.select_option("select[name=setor_id]", escala["setor"])
    page.fill("input[name=data_inicio]", escala["inicio"])
    page.fill("input[name=data_fim]", escala["fim"])
    for i, (data, ini, fim, tipo, vagas, _) in enumerate(escala["turnos"]):
        page.click("text=Adicionar turno")
        linha = page.locator(".turno-linha").nth(i)
        linha.wait_for()
        linha.locator("input[name=turno_data]").fill(data)
        linha.locator("input[name=turno_inicio]").fill(ini)
        linha.locator("input[name=turno_fim]").fill(fim)
        linha.locator("select[name=turno_tipo]").select_option(tipo)
        linha.locator("input[name=turno_vagas]").fill(vagas)


def atribuir(page: Page, posicao: int, servidor_id: int, total: int) -> None:
    cartao = page.locator("article[id^=turno-]").nth(posicao)
    cartao.locator("select[name=servidor_id]").select_option(str(servidor_id))
    cartao.get_by_role("button", name="Atribuir").click()
    page.wait_for_function(
        "([i, n]) => document.querySelectorAll('article[id^=turno-]')[i]"
        ".querySelectorAll('li button').length >= n",
        arg=[posicao, total],
    )


def main() -> None:
    PASTA.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        navegador = pw.chromium.launch(channel="chrome")
        page = navegador.new_page(viewport={"width": 1280, "height": 900})

        page.goto(f"{BASE}/escalas")
        print_tela(page, "escalas-lista-inicial")

        # Validação: data final anterior à inicial não grava nada
        page.fill("input[name=nome]", "Escala inválida (teste)")
        page.select_option("select[name=setor_id]", CAC)
        page.fill("input[name=data_inicio]", "2026-11-08")
        page.fill("input[name=data_fim]", "2026-11-02")
        page.click("button[type=submit]")
        page.wait_for_selector("#resultado .erro")
        print_tela(page, "validacao-data-final-anterior")
        page.reload()

        # Validação: turno fora do período não grava nada
        preencher_escala(
            page,
            {
                **ESCALAS[0],
                "nome": "Escala inválida (teste)",
                "turnos": [("2026-11-20", "08:00", "12:00", "manhã", "1", [])],
            },
        )
        page.click("button[type=submit]")
        page.wait_for_selector("#resultado .erro")
        print_tela(page, "validacao-turno-fora-do-periodo")
        page.reload()

        for escala in ESCALAS:
            preencher_escala(page, escala)
            print_tela(page, f"formulario-{escala['nome'][:3].lower()}-preenchido")
            page.click("button[type=submit]")
            page.wait_for_selector("#resultado .sucesso")
            print_tela(page, f"escala-{escala['nome'][:3].lower()}-cadastrada")
            page.reload()

            page.get_by_role("link", name=escala["nome"]).first.click()
            page.wait_for_selector("article[id^=turno-]")
            for posicao, turno in enumerate(escala["turnos"]):
                for n, servidor_id in enumerate(turno[5], start=1):
                    atribuir(page, posicao, servidor_id, n)
            print_tela(page, f"atribuicoes-{escala['nome'][:3].lower()}")

            if escala["setor"] == CAC:
                # turno da noite tem 1 vaga e já está ocupado: a recusa aparece no cartão
                cartao = page.locator("article[id^=turno-]").nth(2)
                cartao.locator("select[name=servidor_id]").select_option("2")
                cartao.get_by_role("button", name="Atribuir").click()
                cartao.locator(".erro").wait_for()
                print_tela(page, "recusa-turno-sem-vagas")

            page.get_by_role("button", name="Publicar escala").click()
            page.wait_for_selector("text=publicada")
            print_tela(page, f"escala-{escala['nome'][:3].lower()}-publicada")
            page.goto(f"{BASE}/escalas")

        print_tela(page, "escalas-lista-final")
        page.goto(f"{BASE}/?inicio=2026-11-02&fim=2026-11-08")
        page.wait_for_selector("canvas")
        page.wait_for_timeout(800)  # animação do gráfico
        print_tela(page, "dashboard-semana-45")
        page.goto(f"{BASE}/?inicio=2026-10-26&fim=2026-11-01")
        page.wait_for_timeout(800)
        print_tela(page, "dashboard-semana-44-seed")
        page.goto(f"{BASE}/agenda?semana=2026-11-02")
        print_tela(page, "agenda-semana-45")
        page.goto(f"{BASE}/agenda?semana=2026-10-26&setor_id={PRO}")
        print_tela(page, "agenda-semana-44-setor-pro")

        navegador.close()


if __name__ == "__main__":
    main()
