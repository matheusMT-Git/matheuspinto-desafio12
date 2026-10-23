# Sistema de Escalas de Atendimento (MVP)

Aplicação web em Python/FastAPI para montar escalas de atendimento: cadastrar a escala, atribuir
servidores a turnos (com validação de vagas e de choque de horário) e consultar a agenda, com um
dashboard de turnos programados, pessoas escaladas e vagas. Roda localmente com SQLite e dados
fictícios.

## Instalação

Requer Python 3.11 ou superior.

```bash
python -m venv .venv
.venv/Scripts/activate        # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
```

## Dados fictícios (seed)

```bash
python -m app.seed
```

Apaga o banco `escalas.db`, aplica as migrações do Alembic e carrega 2 setores, 10 servidores,
2 escalas, 12 turnos e 23 atribuições (22 confirmadas, 1 cancelada), cobrindo a semana de
26/10 a 01/11/2026. Sem o seed, crie o banco vazio com `alembic upgrade head`.

## Execução

```bash
uvicorn app.main:app --reload
```

- Telas: `/` (dashboard), `/escalas`, `/escalas/{id}`, `/agenda`
- Documentação da API: `/docs`

## Testes e qualidade

```bash
ruff check .
pytest -q
```

## Roteiro da demonstração (sobre o seed)

O dashboard abre na semana corrente; como os dados fictícios são da semana de 26/10/2026,
informe o período nos filtros.

1. **Dashboard** — em `/?inicio=2026-10-26&fim=2026-11-01`: 12 turnos programados, 8 pessoas
   escaladas, 9 vagas livres de 31 (71% ocupado, cartão em alerta âmbar), gráfico por dia e a lista
   "Turnos com vaga aberta".
2. **Agenda** — em `/agenda?semana=2026-10-26`: os 12 turnos distribuídos de segunda a domingo.
   Filtre pelo servidor S01 (T01, T03 e T06) e pelo setor PRO (5 turnos).
3. **Cadastrar escala (CA1)** — em `/escalas`, crie uma escala com turnos. Teste uma data final
   anterior à inicial e um turno fora do período: a tela mostra a mensagem e nada é gravado.
4. **Atribuir turno (CA2)** — em `/escalas/1` (ou `/escalas/2`), tente:
   - S06 no T01 → 409 "Turno sem vagas.";
   - S07 no T01 (escala 1) → 409 "Choque de horário…" com o T08;
   - S10 no T09 (escala 2) → 422 "Servidor inativo não pode ser escalado.".

   O seletor da tela só lista servidores ativos; os dois primeiros casos podem ser feitos nela, e
   o terceiro pela API (`POST /api/v1/turnos/{id}/atribuicoes`, em `/docs`).
5. **Consistência (CA3)** — atribua S04 ao T03 e volte ao dashboard (9 → 8 vagas livres) e à
   agenda (T03 sem vagas); cancele a atribuição e confira que tudo volta ao original.

## Estrutura

```text
app/
├── main.py        # cria o app, monta rotas e templates
├── database.py    # engine, SessionLocal, get_db
├── seed.py        # dados fictícios
├── models/        # Setor, Servidor, Escala, Turno, Atribuicao
├── schemas/       # Pydantic: *Create, *Update, *Read
├── services/      # regras de negócio (escalas, atribuicoes, agenda, dashboard)
├── api/v1/        # rotas REST
├── web/           # rotas que devolvem HTML
├── templates/     # Jinja2 + HTMX
└── static/
alembic/           # migrações
tests/             # CA1, CA2 e CA3
```
