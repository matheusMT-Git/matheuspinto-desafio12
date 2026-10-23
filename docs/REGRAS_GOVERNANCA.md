# Regras de Governança · GOVSAFE 360 v15 · DIDÁTICAS

A **única lógica de decisão** está em `js/politica.js`, utilizada tanto no browser quanto pelo servidor MCP. `npm run test:policy` verifica 8 casos equivalentes. Resultado de exercício não substitui normas e autorizações da SEMA/MT.

1. `credencial`, `pessoal` ou `critica` ⇒ **NÃO AUTORIZADO**, independentemente de campo aprovação humana.
2. `producao` com `edicao` ou `execucao` ⇒ **NÃO AUTORIZADO**.
3. `producao` em `leitura`/`proposta` ⇒ **CONDICIONADO** (sem autorização para ação real).
4. `interno`, `externo`, `homologacao`, `edicao` ou `execucao` não cobertos por regra mais estrita ⇒ **CONDICIONADO**.
5. `publico` + `desenvolvimento` + `leitura`/`proposta` ⇒ **PERMITIDO**, apenas como classificação didática.

**Taxonomia:** dados `publico | interno | pessoal | credencial | externo`; ambiente `desenvolvimento | homologacao | producao`; autonomia `leitura | proposta | edicao | execucao | critica`.

O campo `aprovacao_humana` do MCP informa que ocorreu uma revisão fictícia, mas **NÃO altera a classificação**. O app registra revisão simulada em `localStorage` e impede aprovação de itens não autorizados.
