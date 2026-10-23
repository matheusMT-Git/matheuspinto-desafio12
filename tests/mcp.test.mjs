// Marco 5: testes do servidor MCP local (node:test; o próprio teste age como cliente MCP).
// Executar: npm run test:mcp
import {test, before, after} from 'node:test';
import assert from 'node:assert/strict';
import {spawn} from 'node:child_process';
import {fileURLToPath} from 'node:url';

await import('../js/politica.js');
const {classificar, TAXONOMIA, ALERTA_EXTERNO} = globalThis.GovsafePolitica;

const SERVIDOR = fileURLToPath(new URL('../tools/govsafe-mcp.mjs', import.meta.url));

// Cliente mínimo: escreve linhas JSON no stdin e casa respostas por id.
class Cliente {
  constructor() {
    this.proc = spawn(process.execPath, [SERVIDOR], {stdio: ['pipe', 'pipe', 'pipe']});
    this.linhas = [];
    this.pendentes = new Map();
    this.semId = [];
    this.proximoId = 1;
    let buffer = '';
    this.proc.stdout.setEncoding('utf8');
    this.proc.stdout.on('data', (pedaco) => {
      buffer += pedaco;
      let fim;
      while ((fim = buffer.indexOf('\n')) >= 0) {
        const linha = buffer.slice(0, fim);
        buffer = buffer.slice(fim + 1);
        this.linhas.push(linha);
        const msg = JSON.parse(linha);
        const espera = this.pendentes.get(msg.id);
        if (espera) {
          this.pendentes.delete(msg.id);
          espera(msg);
        } else this.semId.push(msg);
      }
    });
  }

  bruto(texto) {
    this.proc.stdin.write(texto + '\n');
  }

  pedir(method, params) {
    const id = this.proximoId++;
    return this.pedirComId(id, method, params);
  }

  pedirComId(id, method, params) {
    return new Promise((resolve) => {
      this.pendentes.set(id, resolve);
      this.bruto(JSON.stringify({jsonrpc: '2.0', id, method, ...(params === undefined ? {} : {params})}));
    });
  }

  notificar(method, params) {
    this.bruto(JSON.stringify({jsonrpc: '2.0', method, ...(params === undefined ? {} : {params})}));
  }

  // Envia uma linha que gera resposta com id null e espera por ela.
  async erroSemId(texto) {
    const antes = this.semId.length;
    this.bruto(texto);
    await this.pedir('ping'); // ping depois garante que a resposta anterior já chegou
    return this.semId[antes];
  }

  async ferramenta(name, args) {
    const r = await this.pedir('tools/call', {name, arguments: args});
    return r.result;
  }

  fechar() {
    this.proc.stdin.end();
    return new Promise((resolve) => this.proc.on('exit', resolve));
  }
}

let cliente;
before(async () => {
  cliente = new Cliente();
  const r = await cliente.pedir('initialize', {protocolVersion: '2025-06-18', capabilities: {}, clientInfo: {name: 'teste', version: '1'}});
  assert.equal(r.result.protocolVersion, '2025-06-18');
  cliente.notificar('notifications/initialized');
});
after(async () => {
  const codigo = await cliente.fechar();
  assert.equal(codigo, 0, 'servidor deve encerrar limpo ao fechar o stdin');
});

const dados = (res) => res.structuredContent;

test('initialize: serverInfo, capabilities e negociação de versão', async () => {
  const r = await cliente.pedir('initialize', {protocolVersion: '2024-11-05'});
  assert.equal(r.result.serverInfo.name, 'govsafe360-mcp');
  assert.ok(r.result.capabilities.tools);
  assert.equal(r.result.protocolVersion, '2024-11-05');
  const desconhecida = await cliente.pedir('initialize', {protocolVersion: '1999-01-01'});
  assert.equal(desconhecida.result.protocolVersion, '2025-06-18');
});

test('tools/list: 4 ferramentas com inputSchema (aceite do backlog M5)', async () => {
  const {result} = await cliente.pedir('tools/list');
  const nomes = result.tools.map((t) => t.name).sort();
  assert.deepEqual(nomes, ['classificar_cenario', 'listar_cenarios_exemplo', 'listar_regras', 'validar_revisao']);
  for (const t of result.tools) {
    assert.equal(t.inputSchema.type, 'object', t.name);
    assert.ok(t.description.length > 0, t.name);
    assert.ok(!('executar' in t), 'implementação não vaza na listagem');
  }
  const classificarDef = result.tools.find((t) => t.name === 'classificar_cenario');
  assert.deepEqual(classificarDef.inputSchema.properties.dado.enum, [...TAXONOMIA.dado]);
});

test('classificar_cenario: cenário fictício público é permitido (aceite do backlog M5)', async () => {
  const res = await cliente.ferramenta('classificar_cenario', {
    dado: 'publico', ambiente: 'desenvolvimento', autonomia: 'leitura', finalidade: 'Resumo de boletim fictício'
  });
  assert.equal(res.isError, false);
  assert.equal(dados(res).decisao, 'permitido');
  assert.equal(dados(res).regra, 'R5');
  assert.match(dados(res).aviso, /NÃO é sistema institucional homologado/);
  assert.deepEqual(JSON.parse(res.content[0].text), dados(res), 'texto e structuredContent coincidem');
});

test('paridade: as 75 combinações dão o mesmo resultado que js/politica.js', async () => {
  const pedidos = [];
  for (const dado of TAXONOMIA.dado) {
    for (const ambiente of TAXONOMIA.ambiente) {
      for (const autonomia of TAXONOMIA.autonomia) {
        pedidos.push(cliente.ferramenta('classificar_cenario', {dado, ambiente, autonomia}).then((res) => {
          const esperado = classificar({dado, ambiente, autonomia});
          assert.equal(dados(res).decisao, esperado.decisao, `${dado}/${ambiente}/${autonomia}`);
          assert.equal(dados(res).regra, esperado.regra);
          assert.equal(dados(res).motivo, esperado.motivo);
        }));
      }
    }
  }
  assert.equal(pedidos.length, 75);
  await Promise.all(pedidos);
});

test('aprovacao_humana não altera a classificação (REGRAS_GOVERNANCA)', async () => {
  const base = {dado: 'credencial', ambiente: 'desenvolvimento', autonomia: 'leitura'};
  const sem = dados(await cliente.ferramenta('classificar_cenario', base));
  const com = dados(await cliente.ferramenta('classificar_cenario', {...base, aprovacao_humana: true}));
  assert.equal(com.decisao, 'nao_autorizado');
  assert.equal(com.decisao, sem.decisao);
  assert.equal(com.aprovacao_humana, 'registrada, sem efeito na classificação');
  assert.equal(sem.aprovacao_humana, 'não informada');
  const invalido = await cliente.ferramenta('classificar_cenario', {...base, aprovacao_humana: 'sim'});
  assert.equal(invalido.isError, true);
});

test('externo: condicionado com alerta de ausência de autoridade (CA05)', async () => {
  const r = dados(await cliente.ferramenta('classificar_cenario', {dado: 'externo', ambiente: 'desenvolvimento', autonomia: 'leitura'}));
  assert.equal(r.decisao, 'condicionado');
  assert.ok(r.alertas.includes(ALERTA_EXTERNO));
});

test('valor fora da taxonomia é não autorizado (R0), igual ao navegador', async () => {
  const r = dados(await cliente.ferramenta('classificar_cenario', {dado: 'admin', ambiente: 'producao', autonomia: 'leitura'}));
  assert.equal(r.decisao, 'nao_autorizado');
  assert.equal(r.regra, 'R0');
});

test('validar_revisao: aprovar item credencial é recusado e nada é gravado (CA07)', async () => {
  const base = {dado: 'credencial', ambiente: 'homologacao', autonomia: 'execucao', justificativa: 'Justificativa fictícia suficiente.'};
  const aprovar = dados(await cliente.ferramenta('validar_revisao', {...base, acao: 'aprovar'}));
  assert.equal(aprovar.aceita, false);
  assert.equal(aprovar.codigo, 'aprovacao_bloqueada');
  assert.equal(aprovar.gravado, false);
  const rejeitar = dados(await cliente.ferramenta('validar_revisao', {...base, acao: 'rejeitar'}));
  assert.equal(rejeitar.aceita, true);
  const curta = dados(await cliente.ferramenta('validar_revisao', {...base, acao: 'rejeitar', justificativa: 'curta'}));
  assert.equal(curta.codigo, 'justificativa_invalida');
});

test('possível segredo na finalidade é recusado sem repetir o trecho', async () => {
  for (const finalidade of ['Consultar 123.456.789-09', 'acesso com senha: Segredo123']) {
    const res = await cliente.ferramenta('classificar_cenario', {dado: 'publico', ambiente: 'desenvolvimento', autonomia: 'leitura', finalidade});
    assert.equal(res.isError, true);
    assert.ok(!res.content[0].text.includes('123.456') && !res.content[0].text.includes('Segredo123'));
  }
  const revisao = dados(await cliente.ferramenta('validar_revisao', {
    dado: 'interno', ambiente: 'homologacao', autonomia: 'proposta', acao: 'aprovar', justificativa: 'ok, token = abc123xyz'
  }));
  assert.equal(revisao.codigo, 'possivel_segredo');
});

test('listar_regras e listar_cenarios_exemplo', async () => {
  const regras = dados(await cliente.ferramenta('listar_regras', {}));
  assert.deepEqual(regras.regras.map((r) => r.regra), ['R0', 'R1', 'R2', 'R3', 'R4', 'R5']);
  const exemplos = dados(await cliente.ferramenta('listar_cenarios_exemplo'));
  assert.equal(exemplos.cenarios.length, 8);
  assert.deepEqual(exemplos.cenarios.map((c) => c.decisao).join(','),
    'permitido,permitido,condicionado,condicionado,condicionado,nao_autorizado,nao_autorizado,nao_autorizado');
});

test('erros de chamada: campo faltando vira isError; ferramenta e argumentos inválidos viram -32602', async () => {
  const faltando = await cliente.ferramenta('classificar_cenario', {dado: 'publico'});
  assert.equal(faltando.isError, true);
  const desconhecida = await cliente.pedir('tools/call', {name: 'apagar_tudo', arguments: {}});
  assert.equal(desconhecida.error.code, -32602);
  const semNome = await cliente.pedir('tools/call', {});
  assert.equal(semNome.error.code, -32602);
  const argsLista = await cliente.pedir('tools/call', {name: 'listar_regras', arguments: []});
  assert.equal(argsLista.error.code, -32602);
});

test('erros de protocolo e o servidor continua respondendo', async () => {
  assert.equal((await cliente.pedir('resources/list')).error.code, -32601);
  assert.equal((await cliente.pedir('__proto__')).error.code, -32601);
  assert.equal((await cliente.erroSemId('{isto não é json')).error.code, -32700);
  assert.equal((await cliente.erroSemId('[1,2]')).error.code, -32600);
  const semVersao = await new Promise((resolve) => {
    cliente.pendentes.set('x', resolve);
    cliente.bruto(JSON.stringify({id: 'x', method: 'ping'}));
  });
  assert.equal(semVersao.error.code, -32600);
  assert.deepEqual((await cliente.pedir('ping')).result, {});
});

test('notificações não recebem resposta e stdout só contém JSON-RPC', async () => {
  const antes = cliente.linhas.length;
  cliente.notificar('notifications/cancelled', {requestId: 999});
  cliente.notificar('metodo/inexistente');
  await cliente.pedir('ping');
  assert.equal(cliente.linhas.length, antes + 1, 'só o ping deve ter resposta');
  for (const linha of cliente.linhas) {
    assert.equal(JSON.parse(linha).jsonrpc, '2.0');
  }
});
