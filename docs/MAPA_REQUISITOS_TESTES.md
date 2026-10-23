# Rastreabilidade requisito → implementação → teste

Testes E2E em `tests/e2e/govsafe.spec.mjs` (rodam em desktop 1280px e mobile 390px). Todo teste E2E também falha se houver requisição externa ou erro de console (R08/CA09).

| Requisito | Código/fonte | Evidência |
|---|---|---|
| REQ01 Dashboard | `index.html`, `js/app.js`, `js/dados.js` | E2E 01 |
| REQ02 Busca | `js/app.js` | E2E 02 |
| REQ03 Filtro decisão | `js/app.js` | E2E 03 |
| REQ04 Cadastro e persistência | `js/app.js`, localStorage | E2E 04 |
| REQ05 Aprovação humana condicionada | `js/app.js`, `js/politica.js` (`validarRevisao`) | E2E 05; `npm run test:policy`; `validar_revisao` em `npm run test:mcp` |
| REQ06 Exportações | `js/app.js`, `js/exportacao.js` | E2E 06; `npm run test:export` |
| REQ07 Responsividade | `css/styles.css` | E2E 07 (projeto mobile 390px) |
| REQ08 Produção sem execução autônoma | `js/politica.js` | E2E 08; `npm run test:policy`; paridade das 75 combinações em `npm run test:mcp` |
| — Offline e console limpo (R08/CA09) | todo o site | E2E 09 e fixture `vigilancia` em todos os E2E |
| — Limpar dados locais (POLITICA_DE_DADOS) | `js/app.js` | E2E 10 (confirmação real: Cancelar e OK) |
| REQ09 Build Vercel | `scripts/*`, `vercel.json` | `npm run build`, `check:sync` (M7, pendente) |
| REQ10 CI | `.github/workflows/qualidade.yml` | GitHub Actions (pendente execução remota no M7; sequência reproduzida localmente no M6) |
