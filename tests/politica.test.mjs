// Marco 2: testes do motor de decisão (node:test, sem dependências externas).
// Executar: npm run test:policy
import {test} from 'node:test';
import assert from 'node:assert/strict';

await import('../js/politica.js');
await import('../js/dados.js');
const {classificar, validarRevisao, detectarPossivelSegredo, TAXONOMIA, DECISOES, ALERTA_EXTERNO} = globalThis.GovsafePolitica;
const {CENARIOS_INICIAIS} = globalThis.GovsafeDados;

const caso = (dado, ambiente, autonomia, extra = {}) => classificar({dado, ambiente, autonomia, ...extra});

test('público: desenvolvimento em leitura/proposta é permitido (R5)', () => {
  assert.equal(caso('publico', 'desenvolvimento', 'leitura').decisao, 'permitido');
  assert.equal(caso('publico', 'desenvolvimento', 'proposta').decisao, 'permitido');
  assert.equal(caso('publico', 'desenvolvimento', 'leitura').regra, 'R5');
});

test('público: homologação ou execução exigem revisão (R4)', () => {
  assert.equal(caso('publico', 'homologacao', 'leitura').decisao, 'condicionado');
  assert.equal(caso('publico', 'desenvolvimento', 'execucao').decisao, 'condicionado');
});

test('credencial é sempre não autorizada (CA02, R1)', () => {
  for (const ambiente of TAXONOMIA.ambiente) {
    for (const autonomia of TAXONOMIA.autonomia) {
      const r = caso('credencial', ambiente, autonomia);
      assert.equal(r.decisao, 'nao_autorizado', `${ambiente}/${autonomia}`);
      assert.equal(r.regra, 'R1');
    }
  }
});

test('aprovação humana NÃO converte não autorizado (CA07)', () => {
  assert.equal(caso('credencial', 'desenvolvimento', 'leitura', {aprovacao_humana: true}).decisao, 'nao_autorizado');
  assert.equal(caso('interno', 'producao', 'execucao', {aprovacao_humana: true}).decisao, 'nao_autorizado');
  assert.deepEqual(
    caso('publico', 'producao', 'leitura', {aprovacao_humana: true}),
    caso('publico', 'producao', 'leitura')
  );
});

test('dado pessoal é não autorizado (R1)', () => {
  assert.equal(caso('pessoal', 'desenvolvimento', 'leitura').decisao, 'nao_autorizado');
});

test('produção: leitura/proposta condicionado; edição/execução não autorizado (CA03, R2/R3)', () => {
  assert.equal(caso('publico', 'producao', 'leitura').decisao, 'condicionado');
  assert.equal(caso('publico', 'producao', 'proposta').regra, 'R3');
  assert.equal(caso('interno', 'producao', 'edicao').decisao, 'nao_autorizado');
  assert.equal(caso('interno', 'producao', 'execucao').regra, 'R2');
});

test('ação crítica é não autorizada em qualquer ambiente (CA04)', () => {
  assert.equal(caso('publico', 'desenvolvimento', 'critica').decisao, 'nao_autorizado');
  assert.equal(caso('publico', 'producao', 'critica').decisao, 'nao_autorizado');
});

test('conteúdo externo: condicionado e sinaliza ausência de autoridade (CA05)', () => {
  const r = caso('externo', 'desenvolvimento', 'leitura');
  assert.equal(r.decisao, 'condicionado');
  assert.ok(r.alertas.includes(ALERTA_EXTERNO));
  assert.equal(caso('publico', 'desenvolvimento', 'leitura').alertas.length, 0);
});

test('entrada inválida ou ausente é não autorizada (R0)', () => {
  assert.equal(caso('secreto', 'desenvolvimento', 'leitura').regra, 'R0');
  assert.equal(caso('publico', 'nuvem', 'leitura').decisao, 'nao_autorizado');
  assert.equal(classificar({}).decisao, 'nao_autorizado');
  assert.equal(classificar(undefined).decisao, 'nao_autorizado');
});

test('os 8 cenários iniciais (js/dados.js) mantêm as decisões esperadas', () => {
  const esperadas = ['permitido', 'permitido', 'condicionado', 'condicionado', 'condicionado',
    'nao_autorizado', 'nao_autorizado', 'nao_autorizado'];
  assert.equal(CENARIOS_INICIAIS.length, 8);
  CENARIOS_INICIAIS.forEach((c, i) => {
    assert.equal(classificar(c).decisao, esperadas[i], `#${c.id} ${c.finalidade}`);
    assert.ok(!('decisao' in c), 'dados iniciais não devem trazer decisão gravada');
  });
});

test('decisão gravada junto da entrada é ignorada pelo motor', () => {
  const forjado = {dado: 'credencial', ambiente: 'desenvolvimento', autonomia: 'leitura', decisao: 'permitido'};
  assert.equal(classificar(forjado).decisao, 'nao_autorizado');
});

test('varredura: as 75 combinações têm decisão válida e motivo; só 2 são permitidas', () => {
  let total = 0, permitidas = 0;
  for (const dado of TAXONOMIA.dado) {
    for (const ambiente of TAXONOMIA.ambiente) {
      for (const autonomia of TAXONOMIA.autonomia) {
        const r = caso(dado, ambiente, autonomia);
        assert.ok(r.decisao in DECISOES);
        assert.ok(r.motivo.length > 0);
        total++;
        if (r.decisao === 'permitido') permitidas++;
      }
    }
  }
  assert.equal(total, 75);
  assert.equal(permitidas, 2);
});

test('resultado é imutável (função pura, sem estado compartilhado)', () => {
  const r = caso('publico', 'desenvolvimento', 'leitura');
  assert.ok(Object.isFrozen(r));
  assert.ok(Object.isFrozen(globalThis.GovsafePolitica));
});

// ---------- Marco 4: revisão humana simulada ----------

const JUST = 'Justificativa fictícia suficiente.';
const credencial = {dado: 'credencial', ambiente: 'desenvolvimento', autonomia: 'leitura'};
const condicionado = {dado: 'interno', ambiente: 'homologacao', autonomia: 'proposta'};

test('revisão: item não autorizado não pode ser aprovado (backlog M4, CA07)', () => {
  for (const c of [credencial, {dado: 'interno', ambiente: 'producao', autonomia: 'execucao'}, {}]) {
    const v = validarRevisao(c, 'aprovar', JUST);
    assert.equal(v.aceita, false);
    assert.equal(v.codigo, 'aprovacao_bloqueada');
  }
  assert.equal(validarRevisao(credencial, 'rejeitar', JUST).aceita, true);
});

test('revisão: condicionado e permitido aceitam aprovar e rejeitar, sem mudar a decisão', () => {
  for (const acao of ['aprovar', 'rejeitar']) {
    const v = validarRevisao(condicionado, acao, JUST);
    assert.equal(v.aceita, true);
    assert.equal(v.decisao, 'condicionado');
    assert.equal(validarRevisao({dado: 'publico', ambiente: 'desenvolvimento', autonomia: 'leitura'}, acao, JUST).aceita, true);
  }
  assert.equal(classificar(condicionado).decisao, 'condicionado');
});

test('revisão: justificativa obrigatória (10 a 500 caracteres) e ação válida', () => {
  assert.equal(validarRevisao(condicionado, 'aprovar', '').codigo, 'justificativa_invalida');
  assert.equal(validarRevisao(condicionado, 'aprovar', '   curta   ').codigo, 'justificativa_invalida');
  assert.equal(validarRevisao(condicionado, 'aprovar', 'x'.repeat(501)).codigo, 'justificativa_invalida');
  assert.equal(validarRevisao(condicionado, 'aprovar', undefined).codigo, 'justificativa_invalida');
  assert.equal(validarRevisao(condicionado, '', JUST).codigo, 'acao_invalida');
  assert.equal(validarRevisao(condicionado, 'executar', JUST).codigo, 'acao_invalida');
});

test('revisão: justificativa com possível segredo é recusada', () => {
  assert.equal(validarRevisao(condicionado, 'rejeitar', 'Revisado, senha: abc12345').codigo, 'possivel_segredo');
});

// ---------- Marco 4: detecção de possível segredo ----------

test('detecta padrões de segredo ou dado pessoal sem repetir o trecho', () => {
  const casos = [
    'CPF 123.456.789-09 do requerente',
    'contato fulano@exemplo.gov.br',
    'Senha: qualquercoisa',
    'api_key=abc',
    'token = xyz',
    'chave sk-AbCdEf1234567890',
    'ghp_abcdefghijklmnop1234',
    'hash 3f2a9c4e8b7d6a5f1e0c9b8a7d6e5f4a3b2c1d0e',
    'base64 QWxhZGRpbjpvcGVuIHNlc2FtZQ9876543210abcd'
  ];
  for (const texto of casos) {
    const r = detectarPossivelSegredo(texto);
    assert.ok(r, `deveria detectar: ${texto}`);
    assert.ok(!r.includes('qualquercoisa') && !r.includes('123.456'), 'motivo não deve repetir o dado');
  }
});

test('não acusa textos fictícios comuns (falsos positivos)', () => {
  const casos = [
    'Rotacionar chave de acesso de integração',
    'Conferir token de sessão fictício na documentação',
    'Revisão de procedimento interno de protocolo 2026',
    'Processo nº 12345/2026 em homologação',
    'Responsabilidadeadministrativaambiental'
  ];
  for (const texto of casos) assert.equal(detectarPossivelSegredo(texto), null, texto);
  for (const c of CENARIOS_INICIAIS) {
    assert.equal(detectarPossivelSegredo(c.finalidade), null, c.finalidade);
    assert.equal(detectarPossivelSegredo(c.justificativa), null, c.justificativa);
  }
});
