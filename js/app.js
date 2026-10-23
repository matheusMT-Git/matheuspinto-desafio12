// Marco 4: painel, cadastro, filtro, revisão humana simulada, auditoria e exportações.
// Depende de js/politica.js (regras), js/dados.js (cenários iniciais) e js/exportacao.js.
// O localStorage guarda só as ENTRADAS e as revisões; a decisão é sempre recalculada
// pelo motor, então editar o armazenamento não consegue forjar uma decisão.

const {classificar, validarRevisao, detectarPossivelSegredo, DECISOES: ROTULOS, TAXONOMIA} = globalThis.GovsafePolitica;
const {CENARIOS_INICIAIS} = globalThis.GovsafeDados;
const {gerarCsvMatriz, gerarJsonAuditoria, nomeArquivo} = globalThis.GovsafeExportacao;

const CHAVE = 'govsafe360:cenarios:v1';
const CHAVE_AUDITORIA = 'govsafe360:auditoria:v1';
const VERSAO = 1;
const CAMPOS = ['finalidade', 'dado', 'ambiente', 'autonomia', 'justificativa'];
const LIMITES = {finalidade: [5, 120], justificativa: [10, 500]};

const ROTULOS_OPCOES = {
  publico: 'Público', interno: 'Interno', pessoal: 'Pessoal', credencial: 'Credencial', externo: 'Externo',
  desenvolvimento: 'Desenvolvimento', homologacao: 'Homologação', producao: 'Produção',
  leitura: 'Leitura', proposta: 'Proposta', edicao: 'Edição', execucao: 'Execução', critica: 'Crítica'
};
const ROTULOS_REVISAO = {pendente: 'Pendente', aprovado: 'Aprovado', rejeitado: 'Rejeitado'};
const ACAO_DO_STATUS = {aprovado: 'aprovar', rejeitado: 'rejeitar'};
const ROTULOS_EVENTO = {
  cenario_cadastrado: 'Cadastro',
  revisao_aprovada: 'Revisão aprovada',
  revisao_rejeitada: 'Revisão rejeitada',
  revisao_bloqueada: 'Aprovação bloqueada',
  revisao_invalidada: 'Revisão invalidada',
  dados_limpos: 'Dados limpos',
  exportacao_csv: 'Exportação CSV',
  exportacao_json: 'Exportação JSON'
};

let cenarios = [];
let eventos = [];
let emRevisao = null; // id do cenário aberto no diálogo

// ---------- Armazenamento ----------

function copiaIniciais() {
  return CENARIOS_INICIAIS.map((c) => ({...c}));
}

// Lê e valida uma chave versionada. Devolve {itens, falha}; nunca lança.
function lerChave(chave, campo) {
  let bruto;
  try {
    bruto = localStorage.getItem(chave);
  } catch {
    return {itens: null, falha: 'indisponivel'};
  }
  if (bruto === null) return {itens: null, falha: ''};
  try {
    const salvo = JSON.parse(bruto);
    if (salvo?.versao !== VERSAO || !Array.isArray(salvo[campo])) throw new Error('formato');
    return {itens: salvo[campo], falha: ''};
  } catch {
    return {itens: null, falha: 'ilegivel'};
  }
}

function gravarChave(chave, campo, itens) {
  try {
    localStorage.setItem(chave, JSON.stringify({versao: VERSAO, [campo]: itens}));
    return true;
  } catch {
    return false;
  }
}

// Mantém só os campos conhecidos, como texto; qualquer `decisao` gravada é descartada.
function sanitizarCenario(c) {
  const limpo = {id: c.id, ...Object.fromEntries(CAMPOS.map((k) => [k, String(c[k] ?? '')]))};
  const rev = c.revisao;
  if (rev && ACAO_DO_STATUS[rev.status]) {
    limpo.revisao = {status: rev.status, justificativa: String(rev.justificativa ?? ''), data: String(rev.data ?? '')};
  }
  return limpo;
}

function carregar() {
  const avisos = [];
  const lidos = lerChave(CHAVE, 'cenarios');
  if (lidos.falha === 'indisponivel') avisos.push('Armazenamento local indisponível neste navegador; os dados não serão mantidos após recarregar.');
  if (lidos.falha === 'ilegivel') avisos.push('Cenários locais ilegíveis foram ignorados; cenários fictícios iniciais restaurados.');
  const lista = lidos.itens
    ? lidos.itens.filter((c) => c && Number.isInteger(c.id)).map(sanitizarCenario)
    : copiaIniciais();

  const aud = lerChave(CHAVE_AUDITORIA, 'eventos');
  if (aud.falha === 'ilegivel') avisos.push('Histórico de auditoria ilegível foi ignorado.');
  const evs = (aud.itens || [])
    .filter((e) => e && Number.isInteger(e.seq) && typeof e.tipo === 'string')
    .map((e) => ({
      seq: e.seq, data: String(e.data ?? ''), tipo: e.tipo, cenario_id: Number.isInteger(e.cenario_id) ? e.cenario_id : null,
      resumo: String(e.resumo ?? ''), ...(e.justificativa ? {justificativa: String(e.justificativa)} : {})
    }));
  return {lista, evs, avisos};
}

function salvar() {
  return gravarChave(CHAVE, 'cenarios', cenarios);
}

// ---------- Auditoria ----------

function registrarEvento(tipo, cenarioId, resumo, justificativa) {
  const seq = eventos.reduce((max, e) => Math.max(max, e.seq), 0) + 1;
  eventos.push({seq, data: new Date().toISOString(), tipo, cenario_id: cenarioId ?? null, resumo, ...(justificativa ? {justificativa} : {})});
  gravarChave(CHAVE_AUDITORIA, 'eventos', eventos);
  renderAuditoria();
}

// Revisão gravada que a regra não aceitaria (ex.: "aprovado" em item não autorizado,
// editado à mão no localStorage) volta a pendente e fica registrada.
function invalidarRevisoesIrregulares() {
  let alterou = false;
  for (const c of cenarios) {
    if (!c.revisao) continue;
    const v = validarRevisao(c, ACAO_DO_STATUS[c.revisao.status], c.revisao.justificativa);
    if (!v.aceita) {
      registrarEvento('revisao_invalidada', c.id, `Revisão "${c.revisao.status}" do cenário #${c.id} descartada: ${v.motivo}`);
      delete c.revisao;
      alterou = true;
    }
  }
  if (alterou) salvar();
  return alterou;
}

// ---------- Renderização ----------

function comDecisao(c) {
  return {...c, ...classificar(c), statusRevisao: c.revisao?.status || 'pendente'};
}

function celula(texto, classe) {
  const td = document.createElement('td');
  td.textContent = texto;
  if (classe) td.className = classe;
  return td;
}

function rotulo(valor) {
  return ROTULOS_OPCOES[valor] || valor;
}

function renderTabela(lista) {
  const tbody = document.getElementById('tabela-cenarios');
  tbody.replaceChildren();
  if (lista.length === 0) {
    const tr = document.createElement('tr');
    const td = celula('Nenhum cenário corresponde ao filtro.', 'estado-vazio');
    td.colSpan = 8;
    tr.append(td);
    tbody.append(tr);
    return;
  }
  for (const c of lista) {
    const tr = document.createElement('tr');
    tr.append(celula(c.id), celula(c.finalidade), celula(rotulo(c.dado)), celula(rotulo(c.ambiente)), celula(rotulo(c.autonomia)));

    const selo = document.createElement('span');
    selo.className = 'selo selo-' + c.decisao.replace('_', '-');
    selo.textContent = ROTULOS[c.decisao];
    selo.title = `${c.regra}: ${c.motivo}`;
    const tdDecisao = document.createElement('td');
    tdDecisao.append(selo);

    const tdRevisao = celula(ROTULOS_REVISAO[c.statusRevisao], 'revisao-' + c.statusRevisao);
    if (c.revisao) tdRevisao.title = c.revisao.justificativa;

    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'botao botao-pequeno';
    botao.textContent = 'Revisar';
    botao.dataset.revisar = c.id;
    botao.setAttribute('aria-label', `Revisar cenário #${c.id}`);
    const tdAcao = document.createElement('td');
    tdAcao.append(botao);

    tr.append(tdDecisao, tdRevisao, tdAcao);
    tbody.append(tr);
  }
}

function renderTotais(lista) {
  const contar = (decisao) => lista.filter((c) => c.decisao === decisao).length;
  document.getElementById('total-geral').textContent = lista.length;
  document.getElementById('total-permitido').textContent = contar('permitido');
  document.getElementById('total-condicionado').textContent = contar('condicionado');
  document.getElementById('total-nao-autorizado').textContent = contar('nao_autorizado');
}

function normalizar(texto) {
  return texto.toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function aplicarFiltro(lista) {
  const termo = normalizar(document.getElementById('busca').value.trim());
  const decisao = document.getElementById('filtro-decisao').value;
  return lista.filter((c) =>
    (!decisao || c.decisao === decisao) &&
    (!termo || normalizar(`${c.finalidade} ${c.justificativa}`).includes(termo))
  );
}

// Totais sempre sobre todos os cenários; o filtro afeta só a tabela.
function render() {
  const todos = cenarios.map(comDecisao);
  const visiveis = aplicarFiltro(todos);
  renderTotais(todos);
  renderTabela(visiveis);
  document.getElementById('contador').textContent = `Exibindo ${visiveis.length} de ${todos.length} cenários.`;
}

function renderAuditoria() {
  const lista = document.getElementById('lista-auditoria');
  lista.replaceChildren();
  document.getElementById('total-eventos').textContent = `${eventos.length} evento(s) registrado(s).`;
  if (eventos.length === 0) {
    const li = document.createElement('li');
    li.className = 'estado-vazio';
    li.textContent = 'Nenhum evento registrado.';
    lista.append(li);
    return;
  }
  for (const e of [...eventos].reverse()) {
    const li = document.createElement('li');
    const cabecalho = document.createElement('p');
    cabecalho.className = 'evento-cabecalho';
    const quando = document.createElement('time');
    quando.dateTime = e.data;
    const data = new Date(e.data);
    quando.textContent = Number.isNaN(data.getTime()) ? e.data : data.toLocaleString('pt-BR');
    const tipo = document.createElement('strong');
    tipo.textContent = ROTULOS_EVENTO[e.tipo] || e.tipo;
    cabecalho.append(`#${e.seq} · `, quando, ' · ', tipo);
    const resumo = document.createElement('p');
    resumo.textContent = e.resumo;
    li.append(cabecalho, resumo);
    if (e.justificativa) {
      const just = document.createElement('p');
      just.className = 'evento-justificativa';
      just.textContent = `Justificativa: ${e.justificativa}`;
      li.append(just);
    }
    lista.append(li);
  }
}

function mostrarMensagem(id, texto, tipo) {
  const el = document.getElementById(id);
  el.textContent = texto;
  el.className = texto ? `mensagem mensagem-${tipo}` : 'mensagem';
}

// ---------- Cadastro ----------

function preencherOpcoes() {
  for (const campo of ['dado', 'ambiente', 'autonomia']) {
    const select = document.getElementById(`campo-${campo}`);
    for (const valor of TAXONOMIA[campo]) {
      select.append(new Option(rotulo(valor), valor));
    }
  }
}

function validar(entrada) {
  const erros = {};
  for (const [campo, [min, max]] of Object.entries(LIMITES)) {
    const n = entrada[campo].length;
    if (n < min || n > max) erros[campo] = `Informe entre ${min} e ${max} caracteres (atual: ${n}).`;
    else {
      const segredo = detectarPossivelSegredo(entrada[campo]);
      if (segredo) erros[campo] = segredo;
    }
  }
  for (const campo of ['dado', 'ambiente', 'autonomia']) {
    if (!TAXONOMIA[campo].includes(entrada[campo])) erros[campo] = 'Selecione uma opção.';
  }
  return erros;
}

function mostrarErros(erros) {
  for (const campo of CAMPOS) {
    const input = document.getElementById(`campo-${campo}`);
    const erro = document.getElementById(`erro-${campo}`);
    erro.textContent = erros[campo] || '';
    input.setAttribute('aria-invalid', erros[campo] ? 'true' : 'false');
  }
  const primeiro = CAMPOS.find((campo) => erros[campo]);
  if (primeiro) document.getElementById(`campo-${primeiro}`).focus();
}

function aoCadastrar(evento) {
  evento.preventDefault();
  const form = evento.target;
  const entrada = Object.fromEntries(CAMPOS.map((k) => [k, form.elements[k].value.trim()]));
  const erros = validar(entrada);
  mostrarErros(erros);
  if (Object.keys(erros).length > 0) {
    mostrarMensagem('mensagem-cadastro', 'Corrija os campos indicados.', 'erro');
    return;
  }

  const id = cenarios.reduce((max, c) => Math.max(max, c.id), 0) + 1;
  cenarios.push({id, ...entrada});
  const persistiu = salvar();
  const r = classificar(entrada);
  registrarEvento('cenario_cadastrado', id, `Cenário #${id} cadastrado: ${ROTULOS[r.decisao]} (${r.regra}).`);
  render();
  form.reset();

  const partes = [`Cenário #${id} classificado como ${ROTULOS[r.decisao]} (${r.regra}): ${r.motivo}`, ...r.alertas];
  if (!persistiu) partes.push('Atenção: não foi possível salvar no armazenamento local.');
  mostrarMensagem('mensagem-cadastro', partes.join(' '), r.decisao === 'nao_autorizado' ? 'alerta' : 'sucesso');
}

// ---------- Revisão humana simulada ----------

function abrirRevisao(id) {
  const c = cenarios.find((x) => x.id === id);
  if (!c) return;
  emRevisao = id;
  const r = classificar(c);
  const form = document.getElementById('form-revisao');
  form.reset();
  document.getElementById('erro-revisao').textContent = '';
  document.getElementById('revisao-justificativa').setAttribute('aria-invalid', 'false');
  document.getElementById('revisao-resumo').textContent =
    `Cenário #${c.id} — ${c.finalidade}. Decisão do motor: ${ROTULOS[r.decisao]} (${r.regra}): ${r.motivo}`;
  document.getElementById('revisao-atual').textContent = c.revisao
    ? `Revisão atual: ${ROTULOS_REVISAO[c.revisao.status]}. Uma nova revisão substitui a atual e fica registrada na auditoria.`
    : 'Revisão atual: Pendente.';

  const bloqueado = r.decisao === 'nao_autorizado';
  document.getElementById('revisao-aprovar').disabled = bloqueado;
  document.getElementById('revisao-bloqueio').textContent = bloqueado
    ? 'Aprovar está indisponível: item não autorizado não pode ser aprovado. Apenas a rejeição pode ser registrada.'
    : '';
  document.getElementById('dialogo-revisao').showModal();
}

function aoRegistrarRevisao(evento) {
  evento.preventDefault();
  const c = cenarios.find((x) => x.id === emRevisao);
  if (!c) return;
  const form = evento.target;
  const acao = form.elements.acao.value;
  const justificativa = form.elements.justificativa.value.trim();

  // A regra é aplicada aqui, não só no botão desabilitado.
  const v = validarRevisao(c, acao, justificativa);
  if (!v.aceita) {
    if (v.codigo === 'aprovacao_bloqueada') {
      registrarEvento('revisao_bloqueada', c.id, `Tentativa de aprovar o cenário #${c.id} bloqueada (decisão: ${ROTULOS[v.decisao]}).`);
    }
    document.getElementById('erro-revisao').textContent = v.motivo;
    if (v.codigo !== 'acao_invalida') document.getElementById('revisao-justificativa').setAttribute('aria-invalid', 'true');
    return;
  }

  const status = acao === 'aprovar' ? 'aprovado' : 'rejeitado';
  c.revisao = {status, justificativa, data: new Date().toISOString()};
  salvar();
  registrarEvento(status === 'aprovado' ? 'revisao_aprovada' : 'revisao_rejeitada', c.id,
    `Cenário #${c.id} ${status} na revisão humana simulada (decisão mantida: ${ROTULOS[v.decisao]}).`, justificativa);
  render();
  document.getElementById('dialogo-revisao').close();
  mostrarMensagem('mensagem-revisao', `Revisão do cenário #${c.id} registrada: ${ROTULOS_REVISAO[status]}. A decisão do motor continua ${ROTULOS[v.decisao]}.`, 'sucesso');
}

function aoFecharRevisao() {
  // Devolve o foco ao botão "Revisar" da linha (recriado pelo render).
  const botao = document.querySelector(`[data-revisar="${emRevisao}"]`);
  emRevisao = null;
  if (botao) botao.focus();
}

// ---------- Exportações ----------

function baixar(conteudo, tipo, nome) {
  const url = URL.createObjectURL(new Blob([conteudo], {type: tipo}));
  const a = document.createElement('a');
  a.href = url;
  a.download = nome;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function aoExportarCsv() {
  const nome = nomeArquivo('matriz', 'csv', new Date());
  registrarEvento('exportacao_csv', null, `Matriz exportada em CSV com ${cenarios.length} cenário(s).`);
  baixar(gerarCsvMatriz(cenarios, classificar), 'text/csv;charset=utf-8', nome);
}

function aoExportarJson() {
  const nome = nomeArquivo('auditoria', 'json', new Date());
  registrarEvento('exportacao_json', null, `Auditoria exportada em JSON com ${eventos.length + 1} evento(s).`);
  baixar(gerarJsonAuditoria(eventos, new Date().toISOString()), 'application/json;charset=utf-8', nome);
}

// ---------- Limpeza ----------

function aoLimpar() {
  if (!confirm('Apagar os cenários, revisões e auditoria deste navegador e restaurar os 8 cenários fictícios iniciais?')) return;
  try {
    localStorage.removeItem(CHAVE);
    localStorage.removeItem(CHAVE_AUDITORIA);
  } catch { /* armazenamento indisponível: basta restaurar em memória */ }
  cenarios = copiaIniciais();
  eventos = [];
  registrarEvento('dados_limpos', null, 'Dados locais apagados; cenários fictícios iniciais restaurados.');
  render();
  mostrarMensagem('mensagem-dados', 'Dados locais apagados; cenários fictícios iniciais restaurados.', 'sucesso');
}

// ---------- Inicialização ----------

const inicial = carregar();
cenarios = inicial.lista;
eventos = inicial.evs;
renderAuditoria();
if (invalidarRevisoesIrregulares()) {
  inicial.avisos.push('Revisões irregulares no armazenamento local foram descartadas (ver Auditoria).');
}
mostrarMensagem('mensagem-dados', inicial.avisos.join(' '), 'alerta');
preencherOpcoes();
document.getElementById('form-cadastro').addEventListener('submit', aoCadastrar);
document.getElementById('busca').addEventListener('input', render);
document.getElementById('filtro-decisao').addEventListener('change', render);
document.getElementById('limpar-dados').addEventListener('click', aoLimpar);
document.getElementById('tabela-cenarios').addEventListener('click', (e) => {
  const botao = e.target.closest('[data-revisar]');
  if (botao) abrirRevisao(Number(botao.dataset.revisar));
});
document.getElementById('form-revisao').addEventListener('submit', aoRegistrarRevisao);
document.getElementById('cancelar-revisao').addEventListener('click', () => document.getElementById('dialogo-revisao').close());
document.getElementById('dialogo-revisao').addEventListener('close', aoFecharRevisao);
document.getElementById('exportar-csv').addEventListener('click', aoExportarCsv);
document.getElementById('exportar-json').addEventListener('click', aoExportarJson);
render();
