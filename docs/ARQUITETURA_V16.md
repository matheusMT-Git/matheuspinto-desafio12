# Arquitetura GOVSAFE 360 · laboratório v16

## Visão lógica
- Navegador: `index.html`, `css/styles.css`, `js/app.js`, `js/politica.js`.
- Armazenamento: `localStorage`, somente dados fictícios; NÃO é persistência institucional multiusuário.
- Governança: regra única em `js/politica.js`, consumida pelo frontend e pelo servidor MCP.
- MCP local: `tools/govsafe-mcp.mjs`, subprocesso Node.js, ferramentas didáticas de consulta; não cria controles externos.
- Publicação: `npm run build` replica os arquivos-fonte para `public/` e Vercel publica essa pasta.
- Qualidade: Node scripts, Playwright E2E e GitHub Actions CI.

## Limites arquiteturais
Não há login, banco de dados compartilhado, API REST, RBAC real, auditoria imutável, criptografia de dados ou homologação SEMA. Não confundir decisão didática com autorização institucional.

## Critérios de pronto
1. `npm run build`, `check:sync`, `check:js`, `test:policy`, `test:mcp` aprovados.
2. Navegador: cadastro, busca, filtro, revisão, CSV, JSON, mobile sem rolagem global.
3. Repositório único `govsafe360-u06`, CI verde antes do merge, URL Vercel com versão visível.
4. Evidências com apenas dados fictícios; revisão humana explícita para deploy em produção.
