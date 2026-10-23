// Marco 4: testes das exportações CSV/JSON (node:test, sem dependências externas).
// Executar: npm run test:export
import {test} from 'node:test';
import assert from 'node:assert/strict';

await import('../js/politica.js');
await import('../js/dados.js');
await import('../js/exportacao.js');
const {classificar} = globalThis.GovsafePolitica;
const {CENARIOS_INICIAIS} = globalThis.GovsafeDados;
const {COLUNAS, BOM, SISTEMA, escaparCsv, gerarCsvMatriz, gerarJsonAuditoria, nomeArquivo} = globalThis.GovsafeExportacao;

// Divide o CSV em linhas lógicas respeitando aspas (campos podem conter \r\n).
function lerCsv(texto) {
  assert.ok(texto.startsWith(BOM), 'CSV deve começar com BOM UTF-8');
  const linhas = [];
  let campo = '', linha = [], aspas = false;
  const s = texto.slice(BOM.length);
  for (let i = 0; i < s.length; i++) {
    const ch = s[i];
    if (aspas) {
      if (ch === '"' && s[i + 1] === '"') { campo += '"'; i++; }
      else if (ch === '"') aspas = false;
      else campo += ch;
    } else if (ch === '"') aspas = true;
    else if (ch === ';') { linha.push(campo); campo = ''; }
    else if (ch === '\r' && s[i + 1] === '\n') { linha.push(campo); linhas.push(linha); linha = []; campo = ''; i++; }
    else campo += ch;
  }
  return linhas;
}

test('CSV: cabeçalho e uma linha por cenário (CA08)', () => {
  const linhas = lerCsv(gerarCsvMatriz(CENARIOS_INICIAIS, classificar));
  assert.deepEqual(linhas[0], [...COLUNAS]);
  assert.equal(linhas.length, 1 + CENARIOS_INICIAIS.length);
  for (const l of linhas) assert.equal(l.length, COLUNAS.length);
  const decisoes = linhas.slice(1).map((l) => l[COLUNAS.indexOf('decisao')]);
  assert.deepEqual(decisoes, ['permitido', 'permitido', 'condicionado', 'condicionado', 'condicionado',
    'nao_autorizado', 'nao_autorizado', 'nao_autorizado']);
});

test('CSV: decisão é recalculada, nunca a gravada', () => {
  const forjado = [{id: 1, finalidade: 'x', dado: 'credencial', ambiente: 'desenvolvimento', autonomia: 'leitura', justificativa: 'y', decisao: 'permitido'}];
  const [, linha] = lerCsv(gerarCsvMatriz(forjado, classificar));
  assert.equal(linha[COLUNAS.indexOf('decisao')], 'nao_autorizado');
  assert.equal(linha[COLUNAS.indexOf('regra')], 'R1');
});

test('CSV: revisão (pendente por padrão) e alertas', () => {
  const lista = [
    {id: 1, finalidade: 'a', dado: 'externo', ambiente: 'desenvolvimento', autonomia: 'leitura', justificativa: 'j'},
    {id: 2, finalidade: 'b', dado: 'interno', ambiente: 'homologacao', autonomia: 'proposta', justificativa: 'j',
      revisao: {status: 'aprovado', justificativa: 'ok fictício', data: '2026-10-09T12:00:00.000Z'}}
  ];
  const [, l1, l2] = lerCsv(gerarCsvMatriz(lista, classificar));
  assert.equal(l1[COLUNAS.indexOf('revisao_status')], 'pendente');
  assert.match(l1[COLUNAS.indexOf('alertas')], /não instrução/);
  assert.equal(l2[COLUNAS.indexOf('revisao_status')], 'aprovado');
  assert.equal(l2[COLUNAS.indexOf('revisao_data')], '2026-10-09T12:00:00.000Z');
});

test('CSV: aspas, separador e quebra de linha preservados', () => {
  const texto = 'Texto com "aspas"; ponto e vírgula\r\ne quebra';
  const lista = [{id: 1, finalidade: texto, dado: 'publico', ambiente: 'desenvolvimento', autonomia: 'leitura', justificativa: ''}];
  const [, linha] = lerCsv(gerarCsvMatriz(lista, classificar));
  assert.equal(linha[1], texto);
});

test('CSV: proteção contra injeção de fórmula', () => {
  for (const perigoso of ['=HYPERLINK("x")', '+1+1', '-2+3', '@SUM(A1)', '\tTAB']) {
    assert.equal(escaparCsv(perigoso).slice(0, 2), '"\'', perigoso);
  }
  assert.equal(escaparCsv('normal'), '"normal"');
  assert.equal(escaparCsv(9), '"9"');
  assert.equal(escaparCsv(undefined), '""');
});

test('JSON: estrutura da auditoria (CA08)', () => {
  const eventos = [
    {seq: 1, data: '2026-10-09T12:00:00.000Z', tipo: 'cenario_cadastrado', cenario_id: 9, resumo: 'Cenário #9 cadastrado.'},
    {seq: 2, data: '2026-10-09T12:01:00.000Z', tipo: 'revisao_bloqueada', cenario_id: 7, resumo: 'Bloqueada.'}
  ];
  const json = JSON.parse(gerarJsonAuditoria(eventos, '2026-10-09T12:02:00.000Z'));
  assert.equal(json.sistema, SISTEMA);
  assert.match(json.sistema, /NÃO homologado/);
  assert.equal(json.gerado_em, '2026-10-09T12:02:00.000Z');
  assert.equal(json.total_eventos, 2);
  assert.deepEqual(json.eventos, eventos);
  assert.equal(JSON.parse(gerarJsonAuditoria([], 'x')).total_eventos, 0);
});

test('nome dos arquivos com data local', () => {
  const d = new Date(2026, 9, 9);
  assert.equal(nomeArquivo('matriz', 'csv', d), 'govsafe360-matriz-2026-10-09.csv');
  assert.equal(nomeArquivo('auditoria', 'json', d), 'govsafe360-auditoria-2026-10-09.json');
});
