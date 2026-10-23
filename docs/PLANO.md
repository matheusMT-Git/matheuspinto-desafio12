# Plano executado

Plano seguido na construção do MVP do Sistema de Escalas de Atendimento, conforme o
[CLAUDE.md](../CLAUDE.md): três sprints de entrega, cada uma fechada por um critério de aceite,
mais a preparação do repositório, do deploy e das evidências.

## Preparação

| Passo | Resultado |
| --- | --- |
| Ler o CLAUDE.md e verificar o ambiente | Python 3.11 disponível (o documento pede 3.12); `requires-python` ajustado para `>=3.11` |
| Ambiente virtual e dependências | `.venv` com FastAPI, SQLAlchemy 2, Alembic, Jinja2, pytest, ruff |
| Repositório no GitHub | Conteúdo anterior (GOVSAFE 360) removido num commit, sem force push; projeto novo enviado em seguida |

## Sprint 1 · Fundação e cadastro de escalas (CA1)

1. Projeto e estrutura de pastas: `pyproject.toml`, ruff, pytest e a árvore `app/` e `tests/`.
2. Banco e modelos: SQLAlchemy 2 com SQLite, os 5 modelos (Setor, Servidor, Escala, Turno,
   Atribuicao), chaves estrangeiras ativas e migração inicial do Alembic.
3. Schemas Pydantic `*Create`, `*Update` e `*Read` para cada entidade.
4. Seed (`python -m app.seed`): 2 setores, 10 servidores, 2 escalas, 12 turnos e 23 atribuições
   (22 confirmadas, 1 cancelada), cobrindo a semana de 26/10 a 01/11/2026.
5. Serviço e API de escalas e turnos: criar, listar com filtros, detalhar, publicar e incluir
   turno. Todas as regras ficam em `app/services/escalas.py`; erros viram 409/422 com
   `{"detail": "mensagem em português"}`.
6. Tela `/escalas`: lista, formulário de cadastro e linhas de turno adicionadas por HTMX; tela
   mínima `/escalas/{id}`.
7. Testes do CA1: período inválido, turno fora do período, nada gravado em caso de erro.

## Sprint 2 · Atribuição de turnos (CA2)

1. API de servidores com filtros por setor e situação.
2. Serviço de atribuição: servidor ativo, escala não encerrada, servidor já atribuído, choque de
   horário (inclusive turno que vira o dia) e vagas livres. O choque é verificado antes das
   vagas, para que os casos do seed devolvam a mensagem esperada. Atribuição cancelada é
   reativada quando o mesmo servidor volta ao turno.
3. Endpoints `POST /turnos/{id}/atribuicoes` e `DELETE /atribuicoes/{id}`.
4. Tela `/escalas/{id}`: um cartão por turno com vagas livres, servidores escalados, botão de
   cancelar e seletor de servidor via HTMX, trocando só o cartão do turno.
5. Testes do CA2 com os três casos de recusa do seed.

## Sprint 3 · Agenda e dashboard (CA3)

1. Serviço e endpoint de agenda (período máximo de 31 dias, filtros por servidor e setor).
2. Serviço e endpoint do dashboard por consultas agregadas: turnos programados, pessoas
   escaladas, vagas (total, ocupadas, livres, % de ocupação, nível), série por dia e lista de
   turnos com vaga aberta.
3. Tela `/agenda` em visão semanal, com filtros e navegação entre semanas.
4. Tela `/`: três cartões (vagas em âmbar abaixo de 80% e vermelho abaixo de 50%), gráfico de
   barras com Chart.js e lista "Turnos com vaga aberta" com link para a atribuição.
5. Testes do CA3 e README com instalação, seed e roteiro da demonstração.

## Entregas complementares

| Entrega | O que foi feito |
| --- | --- |
| Verificação visual | Servidor local subido e dashboard e agenda do seed conferidos no navegador |
| Deploy no Vercel | Com a variável `VERCEL`, o app usa SQLite em `/tmp` e carrega o seed ao iniciar a instância |
| Dados fictícios e evidências | Duas escalas da semana 45 cadastradas pela interface com Playwright; 17 prints em `evidencias/playwright/` (script em `scripts/evidencias_playwright.py`) |
| Documentação | Esta pasta `docs/` |

## Decisões e limites

- Sem autenticação, filas, Docker ou banco externo, como o CLAUDE.md determina.
- O dashboard abre na semana corrente; como o seed é de 26/10/2026, o período precisa ser
  informado nos filtros para ver os números do exemplo.
- No Vercel o banco é temporário: alterações feitas nas telas se perdem quando a instância
  reinicia.
- Cada sprint só avançou com `ruff check .` e `pytest -q` passando.
