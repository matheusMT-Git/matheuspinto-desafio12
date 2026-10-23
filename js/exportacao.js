// Marco 4: geração do CSV da matriz e do JSON da auditoria (R06/CA08).
// Funções puras: recebem dados e devolvem texto; o download fica em js/app.js.

(function () {
  const SEPARADOR = ';';
  const BOM = '﻿'; // para o Excel pt-BR reconhecer UTF-8 (acentos)
  const SISTEMA = 'GOVSAFE 360 — laboratório didático, NÃO homologado';
  const VERSAO_AUDITORIA = 1;

  const COLUNAS = Object.freeze([
    'id', 'finalidade', 'dado', 'ambiente', 'autonomia', 'decisao', 'regra', 'motivo', 'alertas',
    'revisao_status', 'revisao_justificativa', 'revisao_data'
  ]);

  // RFC 4180 (aspas duplicadas) + proteção contra injeção de fórmula em planilhas.
  function escaparCsv(valor) {
    let s = String(valor ?? '');
    if (/^[=+\-@\t\r]/.test(s)) s = "'" + s;
    return '"' + s.replace(/"/g, '""') + '"';
  }

  // `classificar` é injetado: a decisão exportada é sempre recalculada, nunca a gravada.
  function gerarCsvMatriz(cenarios, classificar) {
    const linhas = [COLUNAS.map(escaparCsv).join(SEPARADOR)];
    for (const c of cenarios) {
      const r = classificar(c);
      const rev = c.revisao || {};
      const valores = [
        c.id, c.finalidade, c.dado, c.ambiente, c.autonomia, r.decisao, r.regra, r.motivo, r.alertas.join(' | '),
        rev.status || 'pendente', rev.justificativa || '', rev.data || ''
      ];
      linhas.push(valores.map(escaparCsv).join(SEPARADOR));
    }
    return BOM + linhas.join('\r\n') + '\r\n';
  }

  function gerarJsonAuditoria(eventos, geradoEm) {
    return JSON.stringify({
      sistema: SISTEMA,
      gerado_em: geradoEm,
      versao: VERSAO_AUDITORIA,
      total_eventos: eventos.length,
      eventos
    }, null, 2);
  }

  function nomeArquivo(prefixo, extensao, data) {
    const p = (n) => String(n).padStart(2, '0');
    return `govsafe360-${prefixo}-${data.getFullYear()}-${p(data.getMonth() + 1)}-${p(data.getDate())}.${extensao}`;
  }

  globalThis.GovsafeExportacao = Object.freeze({
    COLUNAS, SEPARADOR, BOM, SISTEMA, escaparCsv, gerarCsvMatriz, gerarJsonAuditoria, nomeArquivo
  });
})();
