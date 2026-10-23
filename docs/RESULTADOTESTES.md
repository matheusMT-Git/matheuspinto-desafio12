# Resultado dos testes

Última execução: `pytest -q` e `ruff check .` sobre o commit mais recente.

| Verificação | Resultado |
| --- | --- |
| `pytest -q` | **62 passaram, 0 falharam** (1 aviso de depreciação do `httpx` no TestClient) |
| `ruff check .` | Sem pendências |
| `ruff format --check .` | Todos os arquivos formatados |

## Testes automatizados por critério de aceite

| Arquivo | Critério | Testes | Resultado |
| --- | --- | --- | --- |
| `tests/test_escalas.py` | CA1 – cadastrar escala com turnos válidos | 23 | Todos passam |
| `tests/test_atribuicoes.py` | CA2 – atribuir respeitando vagas e horários | 18 | Todos passam |
| `tests/test_agenda_dashboard.py` | CA3 – agenda e indicadores consistentes | 21 | Todos passam |

### O que está coberto

- **CA1:** seed conforme a especificação; escala criada como rascunho e listada; período de 31
  dias aceito e de 32 recusado; data final anterior à inicial; turno fora do período sem gravar
  nada; zero vagas; horário final menor (só o turno da noite pode virar o dia); setor
  inexistente e nome vazio; campo ausente devolve 422 em português; filtros da listagem;
  detalhe com atribuições; 404; publicar e transição de status inválida (409); telas de lista,
  cadastro, erros e inclusão de turno.
- **CA2:** atribuição confirmada diminui as vagas livres em 1; os três casos de recusa do seed
  (S06→T01 409 sem vagas, S07→T01 409 choque com T08, S10→T09 422 inativo); recusa não altera
  vagas; servidor já atribuído; turnos em sequência sem sobreposição; 404 de turno e servidor;
  turno noturno que vira o dia em conflito com turno da madrugada; escala encerrada;
  cancelamento libera a vaga; reatribuição reativa a atribuição cancelada; filtros de servidores;
  telas de atribuição e cancelamento com HTMX.
- **CA3:** agenda da semana com os 12 turnos, servidores e vagas livres conferidos um a um com a
  tabela do seed; ordenação; agenda de S01, do setor PRO e de S09 (vazia); atribuição cancelada
  fora da agenda; validação do período; dashboard com 12 turnos, 8 pessoas e 9 livres de 31
  (71%, alerta); série por dia; filtro por setor; lista de turnos com vaga aberta; nível crítico;
  período sem turnos; escala encerrada fora dos indicadores; atribuição e cancelamento refletidos
  em agenda e dashboard; telas `/` e `/agenda`.

## Falhas encontradas e corrigidas

| # | Onde apareceu | Falha | Causa | Correção |
| --- | --- | --- | --- | --- |
| 1 | Sprint 1, `pytest` | `test_tela_de_detalhe_e_inclusao_de_turno` falhou: o turno recém-criado não aparecia na resposta | A coleção `escala.turnos` ficava desatualizada na sessão depois do commit | `db.expire(escala, ["turnos"])` em `criar_turno` (`app/services/escalas.py`) |
| 2 | Sprint 1, `ruff check` | 10 avisos B008 (`Depends()` em argumentos) | Idioma normal do FastAPI, não um defeito | B008 ignorado na configuração do ruff |
| 3 | Sprint 2, `pytest` | `test_cancelar_pela_tela_libera_a_vaga` falhou | A asserção procurava o nome do servidor, que continua no seletor depois do cancelamento | Teste ajustado para checar o marcador `(S04)`, que só aparece em quem está escalado |
| 4 | Sprint 3, `pytest` | 10 testes do dashboard falharam com `TypeError: 'ChunkedIteratorResult' object is not subscriptable` | `dict()` aplicado diretamente ao resultado da consulta | Troca por compreensão de dicionário em `app/services/dashboard.py` |
| 5 | Sprint 3, aviso | `SADeprecationWarning` por `Result.tuples()` | Método obsoleto no SQLAlchemy 2.1 | Chamadas removidas; resta só o aviso do `httpx` |
| 6 | Evidências com Playwright | O botão "Adicionar turno" apagava os campos já preenchidos do formulário | O `hx-on::after-request` do formulário também recebia o evento do botão interno e executava `reset()` | Reset só quando o evento é do próprio formulário e a resposta foi bem-sucedida; as linhas de turno também são limpas depois do cadastro |

A falha 6 não foi detectada pela suíte automatizada: apareceu ao navegar de verdade e só tem
cobertura pelas evidências em `evidencias/playwright/`. Não há teste automatizado para o
comportamento do formulário no navegador.

## Verificações manuais e evidências

| Verificação | Resultado |
| --- | --- |
| Dashboard e agenda do seed no navegador | Passou: 12 turnos, 8 pessoas, 9 livres de 31, cartão âmbar com 71%; agenda igual à tabela do CLAUDE.md |
| Rotas `/`, `/agenda`, `/escalas`, `/escalas/1` e `/docs` sobre o banco real | Passou: todas responderam 200 |
| Simulação do Vercel (`VERCEL=1`, banco temporário ausente) | Passou: seed carregado na inicialização, dashboard e CSS responderam 200 |
| Playwright: 17 prints (validações, cadastro, atribuições, recusa, publicação, dashboard, agenda) | Passou depois da correção 6 |

## Não verificado

- O deploy real no Vercel: só a simulação local foi feita. Se o build ou a execução falhar, o
  log do Vercel indica o motivo.
- Responsividade da agenda em tela larga (7 colunas): conferida só pelo layout estreito do painel
  do navegador.
- Testes automatizados do comportamento HTMX no navegador: não existem; as rotas são testadas
  pelo TestClient e o fluxo foi visto pelo Playwright.
