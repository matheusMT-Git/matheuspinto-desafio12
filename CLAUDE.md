# Contexto do MVP — Sistema de Escalas de Atendimento

Oct 23, 2026 · @Matheus Moraes

## Visão geral

O MVP entrega, em 3 sprints, uma aplicação web em Python/FastAPI para montar escalas de atendimento: cadastrar a escala, atribuir servidores a turnos e consultar a agenda, com um dashboard de turnos programados, pessoas escaladas e vagas.

O público é o coordenador de um setor de atendimento ao público (ex.: central de atendimento de um órgão público), que hoje monta escalas em planilha. O MVP roda localmente com banco SQLite e dados fictícios carregados por um script de seed.

**No escopo:** cadastro de escalas e turnos, atribuição de servidores com validação de conflito e de vagas, agenda por período/servidor/setor, dashboard com 3 indicadores.

**Fora do escopo:** login e perfis de acesso, troca de turnos entre servidores, banco de horas, notificações por e-mail, integração com RH, app mobile.

## Arquitetura

Um monólito FastAPI em camadas serve a API REST e as páginas HTML no mesmo processo, com SQLite como banco. Sem front-end separado: o HTML é renderizado no servidor e o HTMX troca trechos da página.

&#91;embedded content: arquitetura em camadas · FastAPI monolito\]

As rotas web e a API usam os mesmos serviços, então uma regra (ex.: choque de horário) é escrita e testada uma vez só.

| Camada | Tecnologia |
| --- | --- |
| Linguagem | Python 3.12 |
| Web e API | FastAPI + Uvicorn |
| Validação | Pydantic v2 |
| ORM e banco | SQLAlchemy 2.0 + SQLite (migrações com Alembic) |
| Interface | Jinja2 + HTMX + Pico.css (CDN) |
| Gráficos | Chart.js (CDN) |
| Testes e qualidade | pytest + TestClient do FastAPI, ruff |

**Estrutura de pastas**

```text
escalas-atendimento/
├── CLAUDE.md
├── pyproject.toml
├── app/
│   ├── main.py            # cria o app, monta rotas e templates
│   ├── database.py        # engine, SessionLocal, get_db
│   ├── seed.py            # dados fictícios
│   ├── models/            # setor.py, servidor.py, escala.py, turno.py, atribuicao.py
│   ├── schemas/           # Pydantic: *Create, *Update, *Read
│   ├── services/          # escalas.py, atribuicoes.py, agenda.py, dashboard.py
│   ├── api/v1/            # routers REST
│   ├── web/               # rotas que devolvem HTML
│   ├── templates/         # base.html, dashboard.html, escalas/, agenda.html, partials/
│   └── static/            # css e js próprios
└── tests/
    ├── conftest.py        # banco SQLite em memória + seed
    ├── test_escalas.py    # CA1
    ├── test_atribuicoes.py # CA2
    └── test_agenda_dashboard.py # CA3
```

Execução local: `uvicorn app.main:app --reload`, com a documentação da API em `/docs`.

## Entidades

São 5 entidades. A **Escala** agrupa turnos de um setor num período; cada **Turno** tem um número de vagas; a **Atribuição** liga um **Servidor** a um Turno. Vagas livres = vagas do turno − atribuições ativas.

| Entidade | Campos principais | Regras |
| --- | --- | --- |
| Setor | id, nome, sigla | nome único |
| Servidor | id, matricula, nome, cargo, setor\_id, carga\_horaria\_semanal (h), ativo | matrícula única; só servidor ativo pode ser escalado |
| Escala | id, nome, setor\_id, data\_inicio, data\_fim, status (rascunho, publicada, encerrada), criado\_em | data\_fim ≥ data\_inicio; período máximo de 31 dias |
| Turno | id, escala\_id, data, hora\_inicio, hora\_fim, tipo (manhã, tarde, noite, plantão 12h), vagas | data dentro do período da escala; vagas ≥ 1; hora\_fim > hora\_inicio, exceto turno noturno que vira o dia |
| Atribuicao | id, turno\_id, servidor\_id, status (confirmada, cancelada), criado\_em | par (turno\_id, servidor\_id) único; não exceder vagas; servidor não pode ter dois turnos com horário sobreposto |

Relacionamentos: Setor 1–N Servidor, Setor 1–N Escala, Escala 1–N Turno, Turno 1–N Atribuicao, Servidor 1–N Atribuicao.

Modelos SQLAlchemy em `app/models/`, schemas Pydantic separados em `app/schemas/` (Create, Update, Read para cada entidade).

## Operações e endpoints

As 3 operações mínimas viram uma API REST sob `/api/v1` e 4 telas web. Erros de regra de negócio retornam 409 (conflito) ou 422 (validação) com `{"detail": "mensagem em português"}`.

| Operação | Método e rota | Entrada | Saída |
| --- | --- | --- | --- |
| Cadastrar escala | POST /api/v1/escalas | nome, setor\_id, data\_inicio, data\_fim | 201 + escala |
| Listar escalas | GET /api/v1/escalas?setor\_id=&status= | filtros opcionais | lista de escalas |
| Detalhar escala | GET /api/v1/escalas/{id} | — | escala + turnos + atribuições |
| Publicar escala | PATCH /api/v1/escalas/{id}/status | status | escala atualizada |
| Criar turno na escala | POST /api/v1/escalas/{id}/turnos | data, hora\_inicio, hora\_fim, tipo, vagas | 201 + turno |
| Atribuir turno | POST /api/v1/turnos/{id}/atribuicoes | servidor\_id | 201 + atribuição; 409 se sem vaga ou com choque de horário |
| Cancelar atribuição | DELETE /api/v1/atribuicoes/{id} | — | 204 (status vira cancelada) |
| Consultar agenda | GET /api/v1/agenda?inicio=&fim=&servidor\_id=&setor\_id= | período obrigatório, máx. 31 dias | turnos do período com servidores e vagas livres |
| Listar servidores | GET /api/v1/servidores?setor\_id=&ativo= | filtros | lista de servidores |
| Indicadores | GET /api/v1/dashboard?inicio=&fim=&setor\_id= | período | 3 indicadores + série por dia |

Telas web (Jinja2 + HTMX): `/` dashboard, `/escalas` lista e cadastro, `/escalas/{id}` montagem da escala com atribuição de turnos, `/agenda` consulta em visão semanal com filtros.

## Dashboard

O dashboard mostra 3 cartões calculados para o período e setor filtrados (padrão: semana corrente, todos os setores), mais um gráfico de barras de vagas ocupadas × livres por dia.

| Indicador | Fórmula | Exemplo com o seed (semana 26/10 a 01/11/2026) |
| --- | --- | --- |
| Turnos programados | contagem de turnos no período em escalas publicadas ou rascunho | 12 |
| Pessoas escaladas | servidores distintos com ao menos 1 atribuição confirmada no período | 8 |
| Vagas | soma de vagas − atribuições confirmadas; exibir também total e % de ocupação | 9 livres de 31 (71% ocupado) |

Regras de exibição: cartão de vagas fica em alerta (âmbar) quando a ocupação está abaixo de 80% e crítico (vermelho) abaixo de 50%. A lista "Turnos com vaga aberta" abaixo dos cartões leva direto à tela de atribuição.

Cálculo em `app/services/dashboard.py` via consultas agregadas (sem carregar todos os registros); gráfico com Chart.js carregado por CDN.

## Dados fictícios (seed)

O script `python -m app.seed` recria o banco com 2 setores, 10 servidores, 2 escalas, 12 turnos e 23 atribuições (22 confirmadas, 1 cancelada), cobrindo a semana de 26/10 a 01/11/2026. Os números do dashboard acima saem exatamente destes dados.

**Setores:** CAC – Central de Atendimento ao Cidadão; PRO – Protocolo Geral.

**Servidores**

| Matrícula | Nome | Cargo | Setor | Carga (h/sem) | Ativo |
| --- | --- | --- | --- | --- | --- |
| S01 | Ana Paula Ribeiro | Técnica Administrativa | CAC | 40 | sim |
| S02 | Carlos Eduardo Lima | Agente de Atendimento | CAC | 40 | sim |
| S03 | Fernanda Souza | Agente de Atendimento | CAC | 30 | sim |
| S04 | João Pedro Martins | Técnico Administrativo | CAC | 40 | sim |
| S05 | Mariana Costa | Agente de Atendimento | CAC | 30 | sim |
| S06 | Rafael Almeida | Supervisor de Atendimento | CAC | 40 | sim |
| S07 | Beatriz Nogueira | Assistente de Protocolo | PRO | 30 | sim |
| S08 | Lucas Ferreira | Assistente de Protocolo | PRO | 30 | sim |
| S09 | Patrícia Gomes | Analista Administrativa | PRO | 40 | sim (sem turno na semana) |
| S10 | Roberto Dias | Assistente de Protocolo | PRO | 30 | não (afastado) |

**Escalas**

| Id | Nome | Setor | Período | Status |
| --- | --- | --- | --- | --- |
| E1 | Atendimento CAC – Semana 44 | CAC | 26/10 a 01/11/2026 | publicada |
| E2 | Protocolo – Semana 44 | PRO | 26/10 a 30/10/2026 | rascunho |

**Turnos e atribuições** (esta tabela é também o resultado esperado de `GET /api/v1/agenda?inicio=2026-10-26&fim=2026-11-01`)

| Turno | Escala | Data | Horário | Tipo | Vagas | Servidores escalados | Livres |
| --- | --- | --- | --- | --- | --- | --- | --- |
| T01 | E1 | seg 26/10 | 07:00–13:00 | manhã | 3 | S01, S02, S03 | 0 |
| T02 | E1 | seg 26/10 | 13:00–19:00 | tarde | 3 | S04, S05 | 1 |
| T03 | E1 | ter 27/10 | 07:00–13:00 | manhã | 3 | S01, S02 | 1 |
| T04 | E1 | ter 27/10 | 13:00–19:00 | tarde | 3 | S03, S04, S06 | 0 |
| T05 | E1 | qua 28/10 | 07:00–13:00 | manhã | 3 | S05, S06 | 1 |
| T06 | E1 | qua 28/10 | 13:00–19:00 | tarde | 3 | S01 (S03 cancelada) | 2 |
| T07 | E1 | sáb 31/10 | 08:00–20:00 | plantão 12h | 2 | S02 | 1 |
| T08 | E2 | seg 26/10 | 08:00–14:00 | manhã | 2 | S07, S08 | 0 |
| T09 | E2 | ter 27/10 | 08:00–14:00 | manhã | 2 | S07 | 1 |
| T10 | E2 | qua 28/10 | 08:00–14:00 | manhã | 2 | S08 | 1 |
| T11 | E2 | qui 29/10 | 08:00–14:00 | manhã | 2 | S07, S08 | 0 |
| T12 | E2 | sex 30/10 | 08:00–14:00 | manhã | 3 | S07, S08 | 1 |

Totais: 12 turnos, 31 vagas, 22 confirmadas, 9 livres, 8 servidores distintos.

**Consultas de agenda para teste**

| Consulta | Resultado esperado |
| --- | --- |
| agenda de S01, 26/10 a 01/11 | T01, T03, T06 |
| agenda do setor PRO, 26/10 a 30/10 | T08 a T12, 8 atribuições, 3 vagas livres |
| agenda de S09, 26/10 a 01/11 | lista vazia |
| atribuir S06 a T01 | 409 – turno sem vagas |
| atribuir S07 a T01 | 409 – choque com T08 (08:00–14:00 no mesmo dia) |
| atribuir S10 a T09 | 422 – servidor inativo |

## Critérios de aceite

O MVP está pronto quando os 3 critérios abaixo passam em testes automatizados (pytest) e numa demonstração manual sobre o seed.

**CA1 – Cadastrar escala com turnos válidos** Dado um coordenador na tela `/escalas`, quando ele informa nome, setor e período de até 31 dias e adiciona turnos com data dentro do período e vagas ≥ 1, então a escala é salva com status "rascunho" e aparece na lista. Se a data final for anterior à inicial, ou um turno cair fora do período, o sistema bloqueia com mensagem clara e nada é gravado.

**CA2 – Atribuir turno respeitando vagas e horários** Dado um turno com vaga livre e um servidor ativo, quando o coordenador atribui o servidor, então a atribuição fica "confirmada" e as vagas livres diminuem em 1. O sistema recusa com 409 se o turno estiver lotado ou se o servidor já tiver turno com horário sobreposto, e com 422 se o servidor estiver inativo (casos da tabela de testes do seed).

**CA3 – Consultar agenda e ver indicadores consistentes** Dado o seed carregado, quando a agenda da semana 26/10 a 01/11/2026 é consultada, então ela lista os 12 turnos com servidores e vagas livres por turno, e o dashboard do mesmo período mostra 12 turnos programados, 8 pessoas escaladas e 9 vagas livres de 31. Após uma nova atribuição ou cancelamento, agenda e dashboard refletem a mudança na próxima carga da página.

## Sprints

Três sprints de 2 semanas, cada uma fechada por um critério de aceite; a duração é uma suposição e pode ser ajustada ao time.

&#91;embedded content: roadmap · 3 sprints de 2 semanas\]

**Sprint 1 · Fundação e cadastro de escalas** (meta: CA1)

- [x] Criar projeto (pyproject, ruff, pytest) e a estrutura de pastas
- [x] Configurar SQLAlchemy, SQLite e Alembic; criar os 5 modelos
- [x] Escrever `app/seed.py` com os dados fictícios desta especificação
- [x] Serviço e API de escalas e turnos (criar, listar, detalhar, publicar)
- [x] Tela `/escalas` com lista, formulário de cadastro e inclusão de turnos
- [x] Testes do CA1, incluindo período inválido e turno fora do período

**Sprint 2 · Atribuição de turnos** (meta: CA2)

- [x] API de servidores com filtros por setor e situação
- [x] Serviço de atribuição: checar vagas, servidor ativo e choque de horário (inclusive turno que vira o dia)
- [x] Endpoints de atribuir e cancelar
- [x] Tela `/escalas/{id}`: grade de turnos com vagas livres e seletor de servidor via HTMX
- [x] Testes do CA2 com os 3 casos de recusa do seed

**Sprint 3 · Agenda e dashboard** (meta: CA3)

- [x] Serviço e endpoint de agenda (período máx. 31 dias, filtros por servidor e setor)
- [x] Tela `/agenda` em visão semanal
- [x] Serviço e endpoint do dashboard com os 3 indicadores e a série por dia
- [x] Tela `/` com cartões, alertas de ocupação, gráfico e lista de turnos com vaga
- [x] Testes do CA3 conferindo 12 turnos, 8 escalados e 9 vagas livres de 31
- [x] README com instalação, seed e roteiro da demonstração

## Instruções para o Claude Code

Exporte este documento em Markdown e salve como `CLAUDE.md` na raiz do repositório; o Claude Code lê esse arquivo como contexto em toda sessão.

- Trabalhe uma sprint por vez e não avance sem os testes da sprint passando.
- Regras de negócio ficam em `app/services/`; rotas só validam entrada e chamam serviços.
- Nomes de domínio em português (escala, turno, servidor, atribuicao); código, commits e mensagens de erro em português.
- Use type hints em tudo; rode `ruff check .` e `pytest -q` antes de cada commit.
- Datas no formato ISO na API (`2026-10-26`) e dd/mm/aaaa na interface; fuso America/Sao\_Paulo.
- Não adicione autenticação, filas, Docker ou banco externo no MVP.
- Ao terminar uma tarefa, atualize a seção da sprint marcando o item concluído.

Prompt sugerido para iniciar: *"Leia o CLAUDE.md e execute a Sprint 1. Comece criando a estrutura de pastas e os modelos, depois os testes do CA1."*
