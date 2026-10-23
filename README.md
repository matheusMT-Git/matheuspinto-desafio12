# GOVSAFE 360 — projeto do zero (M0)

Este é o **esqueleto intencional** para construir progressivamente com Claude Code. Não há funcionalidades completas ainda. Abra `index.html` no navegador e siga a apostila/prompt 03; espere construir M1–M7 em vários ciclos. A versão funcional de recuperação é outro ZIP.

Veja `docs/BACKLOG_CONSTRUCAO_DO_ZERO.md` e `docs/CRITERIOS_ACEITE.md`. O projeto final esperado será similar ao GOVSAFE360_RECUPERACAO, que não deve ser sobrescrito durante a construção didática.

## Testes (M6)

```bash
npm run check:js   # sintaxe de todos os scripts
npm test           # política, exportações e MCP (node:test, sem dependências)
npm run test:e2e   # Playwright: navegador real, desktop 1280px e mobile 390px
```

O E2E exige uma vez `npm install` e `npx playwright install chromium` (dependências só de desenvolvimento; o site publicado não usa nenhuma). O Playwright sobe sozinho `scripts/servidor-local.mjs` em `http://127.0.0.1:4173`. Os resultados ficam em `evidencias/playwright-resultados/` e o relatório HTML em `evidencias/relatorio-html/` (ambos fora do Git). A CI (`.github/workflows/qualidade.yml`) roda a mesma sequência a cada push e pull request.

## Servidor MCP local (M5)

`tools/govsafe-mcp.mjs` é um servidor MCP por **stdio** (uma mensagem JSON-RPC 2.0 por linha), escrito sem SDK e sem dependências. Ele reutiliza `js/politica.js`, a mesma regra do navegador.

```bash
npm run mcp       # sobe o servidor (aguarda JSON-RPC no stdin; logs no stderr)
npm run test:mcp  # testes do protocolo, das ferramentas e da paridade com o navegador
```

| Ferramenta | O que faz |
|---|---|
| `classificar_cenario` | Classifica um cenário fictício (`dado`, `ambiente`, `autonomia`). `aprovacao_humana` é registrada, mas **não altera** a decisão. |
| `listar_regras` | Taxonomia e regras R0–R5 na ordem de avaliação. |
| `listar_cenarios_exemplo` | Os 8 cenários fictícios de `js/dados.js` com a decisão calculada. |
| `validar_revisao` | Diz se uma revisão fictícia seria aceita. Item não autorizado nunca pode ser aprovado. Não grava nada. |

**Limites:** ferramentas somente de consulta. O servidor não grava estado, não acessa rede nem arquivos e não cria controles externos. Textos com aparência de CPF, e-mail, senha ou chave são recusados. A classificação é didática e não substitui normas nem autorizações da SEMA/MT.
