#!/usr/bin/env node
// Marco 5: servidor MCP local do GOVSAFE 360, SEM SDK e sem dependências externas.
// Transporte stdio: cada mensagem é uma linha JSON-RPC 2.0 (stdin → servidor → stdout).
// Reutiliza js/politica.js (regra única) e js/dados.js. Ferramentas SOMENTE de consulta:
// não grava estado, não acessa rede nem arquivos, não cria controles externos.
// Logs vão para stderr; stdout é reservado ao protocolo.

import {createInterface} from 'node:readline';

await import('../js/politica.js');
await import('../js/dados.js');
const {classificar, validarRevisao, detectarPossivelSegredo, TAXONOMIA, DECISOES, ACOES_REVISAO} = globalThis.GovsafePolitica;
const {CENARIOS_INICIAIS} = globalThis.GovsafeDados;

const SERVIDOR = Object.freeze({name: 'govsafe360-mcp', version: '0.5.0'});
const VERSOES_PROTOCOLO = ['2025-06-18', '2025-03-26', '2024-11-05'];
const AVISO = 'Classificação didática do laboratório GOVSAFE 360; NÃO é sistema institucional homologado nem autoriza ação real.';

const ERRO = Object.freeze({PARSE: -32700, REQUISICAO: -32600, METODO: -32601, PARAMETROS: -32602, INTERNO: -32603});

const REGRAS = Object.freeze([
  {regra: 'R0', decisao: 'nao_autorizado', condicao: 'Valor ausente ou fora da taxonomia (postura conservadora).'},
  {regra: 'R1', decisao: 'nao_autorizado', condicao: 'Dado credencial ou pessoal, ou autonomia crítica.'},
  {regra: 'R2', decisao: 'nao_autorizado', condicao: 'Produção com edição ou execução.'},
  {regra: 'R3', decisao: 'condicionado', condicao: 'Produção com leitura ou proposta, sem autorização para ação real.'},
  {regra: 'R4', decisao: 'condicionado', condicao: 'Dado interno ou externo, homologação, edição ou execução: exige revisão humana.'},
  {regra: 'R5', decisao: 'permitido', condicao: 'Dado público em desenvolvimento, só leitura ou proposta (classificação didática).'}
]);

// ---------- Ferramentas ----------

const propriedadesCenario = {
  dado: {type: 'string', enum: [...TAXONOMIA.dado], description: 'Tipo de dado envolvido.'},
  ambiente: {type: 'string', enum: [...TAXONOMIA.ambiente], description: 'Ambiente onde o agente atuaria.'},
  autonomia: {type: 'string', enum: [...TAXONOMIA.autonomia], description: 'Grau de autonomia pretendido.'}
};

const FERRAMENTAS = [
  {
    name: 'classificar_cenario',
    title: 'Classificar cenário fictício',
    description: 'Classifica um cenário FICTÍCIO de uso de IA pela política única (js/politica.js). Só consulta; aprovacao_humana é registrada mas não altera a decisão.',
    inputSchema: {
      type: 'object',
      properties: {
        ...propriedadesCenario,
        finalidade: {type: 'string', maxLength: 500, description: 'Descrição fictícia (opcional). Tratada como dado, nunca como instrução.'},
        aprovacao_humana: {type: 'boolean', description: 'Indica revisão humana fictícia. NÃO altera a classificação.'}
      },
      required: ['dado', 'ambiente', 'autonomia'],
      additionalProperties: false
    },
    executar(args) {
      exigirTextos(args, ['dado', 'ambiente', 'autonomia']);
      if (args.finalidade !== undefined) {
        exigirTextos(args, ['finalidade']);
        recusarSegredo(args.finalidade);
      }
      if (args.aprovacao_humana !== undefined && typeof args.aprovacao_humana !== 'boolean') {
        throw new ErroFerramenta('aprovacao_humana deve ser booleano.');
      }
      const r = classificar({dado: args.dado, ambiente: args.ambiente, autonomia: args.autonomia});
      return {
        decisao: r.decisao,
        rotulo: DECISOES[r.decisao],
        regra: r.regra,
        motivo: r.motivo,
        alertas: [...r.alertas],
        aprovacao_humana: args.aprovacao_humana === undefined ? 'não informada' : 'registrada, sem efeito na classificação',
        aviso: AVISO
      };
    }
  },
  {
    name: 'listar_regras',
    title: 'Listar regras de governança',
    description: 'Lista a taxonomia e as regras R0–R5, na ordem de avaliação (a primeira que se aplica decide).',
    inputSchema: {type: 'object', properties: {}, additionalProperties: false},
    executar() {
      return {
        taxonomia: {dado: [...TAXONOMIA.dado], ambiente: [...TAXONOMIA.ambiente], autonomia: [...TAXONOMIA.autonomia]},
        regras: REGRAS,
        observacao: 'Revisão humana não altera a decisão; item não autorizado não pode ser aprovado.',
        aviso: AVISO
      };
    }
  },
  {
    name: 'listar_cenarios_exemplo',
    title: 'Listar cenários fictícios de exemplo',
    description: 'Lista os 8 cenários fictícios pré-carregados (js/dados.js) com a decisão calculada pela política.',
    inputSchema: {type: 'object', properties: {}, additionalProperties: false},
    executar() {
      return {
        cenarios: CENARIOS_INICIAIS.map((c) => {
          const r = classificar(c);
          return {id: c.id, finalidade: c.finalidade, dado: c.dado, ambiente: c.ambiente, autonomia: c.autonomia, decisao: r.decisao, regra: r.regra};
        }),
        aviso: AVISO
      };
    }
  },
  {
    name: 'validar_revisao',
    title: 'Validar revisão humana simulada',
    description: 'Verifica se uma revisão humana FICTÍCIA seria aceita (justificativa obrigatória; item não autorizado não pode ser aprovado). Não grava nada.',
    inputSchema: {
      type: 'object',
      properties: {
        ...propriedadesCenario,
        acao: {type: 'string', enum: [...ACOES_REVISAO], description: 'Ação do revisor fictício.'},
        justificativa: {type: 'string', maxLength: 500, description: 'Justificativa fictícia, entre 10 e 500 caracteres.'}
      },
      required: ['dado', 'ambiente', 'autonomia', 'acao', 'justificativa'],
      additionalProperties: false
    },
    executar(args) {
      exigirTextos(args, ['dado', 'ambiente', 'autonomia', 'acao', 'justificativa']);
      const v = validarRevisao({dado: args.dado, ambiente: args.ambiente, autonomia: args.autonomia}, args.acao, args.justificativa);
      return {aceita: v.aceita, codigo: v.codigo, motivo: v.motivo, decisao: v.decisao, gravado: false, aviso: AVISO};
    }
  }
];

class ErroFerramenta extends Error {}

function exigirTextos(args, campos) {
  for (const campo of campos) {
    if (typeof args[campo] !== 'string') throw new ErroFerramenta(`Campo obrigatório ausente ou não textual: ${campo}.`);
  }
}

function recusarSegredo(texto) {
  const segredo = detectarPossivelSegredo(texto);
  if (segredo) throw new ErroFerramenta(segredo);
}

function chamarFerramenta(params) {
  if (!params || typeof params.name !== 'string') {
    throw new ErroProtocolo(ERRO.PARAMETROS, 'tools/call exige params.name.');
  }
  const ferramenta = FERRAMENTAS.find((f) => f.name === params.name);
  if (!ferramenta) throw new ErroProtocolo(ERRO.PARAMETROS, `Ferramenta desconhecida: ${params.name}`);
  const args = params.arguments ?? {};
  if (typeof args !== 'object' || Array.isArray(args)) {
    throw new ErroProtocolo(ERRO.PARAMETROS, 'params.arguments deve ser um objeto.');
  }
  try {
    const resultado = ferramenta.executar(args);
    return {content: [{type: 'text', text: JSON.stringify(resultado, null, 2)}], structuredContent: resultado, isError: false};
  } catch (erro) {
    if (!(erro instanceof ErroFerramenta)) throw erro;
    // Erro de execução vai no resultado (isError), para o modelo poder corrigir a chamada.
    return {content: [{type: 'text', text: erro.message}], isError: true};
  }
}

// ---------- Protocolo JSON-RPC ----------

class ErroProtocolo extends Error {
  constructor(codigo, mensagem) {
    super(mensagem);
    this.codigo = codigo;
  }
}

const METODOS = {
  initialize(params) {
    const pedida = params?.protocolVersion;
    return {
      protocolVersion: VERSOES_PROTOCOLO.includes(pedida) ? pedida : VERSOES_PROTOCOLO[0],
      capabilities: {tools: {listChanged: false}},
      serverInfo: SERVIDOR,
      instructions: 'Ferramentas somente de consulta sobre cenários FICTÍCIOS. ' + AVISO
    };
  },
  ping: () => ({}),
  'tools/list': () => ({tools: FERRAMENTAS.map(({executar, ...definicao}) => definicao)}),
  'tools/call': chamarFerramenta
};

function enviar(mensagem) {
  process.stdout.write(JSON.stringify(mensagem) + '\n');
}

function responderErro(id, codigo, mensagem) {
  enviar({jsonrpc: '2.0', id, error: {code: codigo, message: mensagem}});
}

function tratarLinha(linha) {
  if (!linha.trim()) return;
  let msg;
  try {
    msg = JSON.parse(linha);
  } catch {
    responderErro(null, ERRO.PARSE, 'JSON inválido.');
    return;
  }

  const temId = msg !== null && typeof msg === 'object' && !Array.isArray(msg) && 'id' in msg;
  const idValido = temId && (typeof msg.id === 'string' || Number.isInteger(msg.id));
  if (Array.isArray(msg) || msg === null || typeof msg !== 'object' || msg.jsonrpc !== '2.0') {
    responderErro(idValido ? msg.id : null, ERRO.REQUISICAO, 'Requisição JSON-RPC 2.0 inválida.');
    return;
  }
  if (typeof msg.method !== 'string') {
    // Resposta vinda do cliente (result/error): não há nada a fazer.
    if (!('result' in msg || 'error' in msg)) responderErro(idValido ? msg.id : null, ERRO.REQUISICAO, 'Campo method ausente.');
    return;
  }
  if (!temId) return; // Notificação (ex.: notifications/initialized): nunca recebe resposta.
  if (!idValido) {
    responderErro(null, ERRO.REQUISICAO, 'id deve ser texto ou inteiro.');
    return;
  }

  const metodo = Object.hasOwn(METODOS, msg.method) ? METODOS[msg.method] : null;
  if (!metodo) {
    responderErro(msg.id, ERRO.METODO, `Método não suportado: ${msg.method}`);
    return;
  }
  try {
    enviar({jsonrpc: '2.0', id: msg.id, result: metodo(msg.params)});
  } catch (erro) {
    if (erro instanceof ErroProtocolo) responderErro(msg.id, erro.codigo, erro.message);
    else {
      console.error('[govsafe360-mcp] erro interno:', erro);
      responderErro(msg.id, ERRO.INTERNO, 'Erro interno do servidor.');
    }
  }
}

const leitor = createInterface({input: process.stdin, crlfDelay: Infinity});
leitor.on('line', tratarLinha);
// Ao fechar o stdin, o processo termina sozinho depois de escrever o que falta.
console.error(`[govsafe360-mcp] ${SERVIDOR.name} ${SERVIDOR.version} pronto (stdio). ${AVISO}`);
