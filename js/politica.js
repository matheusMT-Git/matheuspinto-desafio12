// Marco 2: motor de decisão ÚNICO do GOVSAFE 360 (docs/REGRAS_GOVERNANCA.md).
// Função pura: sem DOM, sem localStorage, sem rede. Classificação DIDÁTICA,
// não substitui normas e autorizações da SEMA/MT.
// Script clássico (sem export) para abrir via file://; o Node o carrega com import().

(function () {
  const TAXONOMIA = Object.freeze({
    dado: Object.freeze(['publico', 'interno', 'pessoal', 'credencial', 'externo']),
    ambiente: Object.freeze(['desenvolvimento', 'homologacao', 'producao']),
    autonomia: Object.freeze(['leitura', 'proposta', 'edicao', 'execucao', 'critica'])
  });

  const DECISOES = Object.freeze({
    permitido: 'Permitido',
    condicionado: 'Condicionado',
    nao_autorizado: 'Não autorizado'
  });

  const ALERTA_EXTERNO = 'Conteúdo externo é dado, não instrução: não possui autoridade para comandar ações do sistema.';

  function resultado(decisao, regra, motivo, alertas) {
    return Object.freeze({decisao, regra, motivo, alertas: Object.freeze(alertas)});
  }

  // A primeira regra que casa decide; a ordem vai da mais restritiva para a menos.
  // `aprovacao_humana` é aceita na entrada, mas NUNCA altera a classificação.
  function classificar(entrada) {
    const {dado, ambiente, autonomia} = entrada || {};
    const alertas = dado === 'externo' ? [ALERTA_EXTERNO] : [];

    // R0: fora da taxonomia ⇒ postura conservadora (R03 do piloto).
    for (const [campo, valor] of [['dado', dado], ['ambiente', ambiente], ['autonomia', autonomia]]) {
      if (!TAXONOMIA[campo].includes(valor)) {
        return resultado('nao_autorizado', 'R0', `Valor de ${campo} ausente ou fora da taxonomia.`, alertas);
      }
    }

    // R1: segredo, dado pessoal ou ação crítica.
    if (dado === 'credencial' || dado === 'pessoal') {
      return resultado('nao_autorizado', 'R1', `Dado do tipo ${dado} não pode ser tratado por agente de IA.`, alertas);
    }
    if (autonomia === 'critica') {
      return resultado('nao_autorizado', 'R1', 'Ação crítica não pode ser delegada a agente de IA.', alertas);
    }

    // R2 e R3: produção.
    if (ambiente === 'producao') {
      if (autonomia === 'edicao' || autonomia === 'execucao') {
        return resultado('nao_autorizado', 'R2', `Autonomia de ${autonomia} em produção não é permitida.`, alertas);
      }
      return resultado('condicionado', 'R3', `Produção apenas em ${autonomia}, sem autorização para ação real.`, alertas);
    }

    // R4: exige revisão humana.
    const gatilhos = [];
    if (dado === 'interno' || dado === 'externo') gatilhos.push(`dado ${dado}`);
    if (ambiente === 'homologacao') gatilhos.push('ambiente de homologação');
    if (autonomia === 'edicao' || autonomia === 'execucao') gatilhos.push(`autonomia de ${autonomia}`);
    if (gatilhos.length > 0) {
      return resultado('condicionado', 'R4', `Exige revisão humana: ${gatilhos.join(', ')}.`, alertas);
    }

    // R5: único caso restante — público + desenvolvimento + leitura/proposta.
    return resultado('permitido', 'R5', 'Dado público em desenvolvimento, apenas leitura ou proposta (classificação didática).', alertas);
  }

  // Marco 4: heurística simples para recusar texto livre com cara de segredo ou dado pessoal.
  // Devolve o motivo (sem repetir o trecho encontrado) ou null. Não substitui o cuidado de quem digita.
  const PADROES_SEGREDO = [
    [/\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b/, 'padrão de CPF'],
    [/[^\s@]+@[^\s@]+\.[^\s@]+/, 'endereço de e-mail'],
    [/\b(senha|password|passwd|token|api[_-]?key|secret|segredo)\s*[:=]/i, 'rótulo de senha, token ou chave'],
    [/\b(sk-|ghp_|gho_|github_pat_|xox[abp]-|AKIA)[A-Za-z0-9_-]{8,}/, 'prefixo de chave de acesso']
  ];

  function detectarPossivelSegredo(texto) {
    const s = String(texto ?? '');
    for (const [padrao, descricao] of PADROES_SEGREDO) {
      if (padrao.test(s)) return `Possível dado sensível (${descricao}). Use apenas dados fictícios.`;
    }
    // Sequência longa com letras e dígitos misturados: provável chave ou hash.
    for (const trecho of s.match(/[A-Za-z0-9+/_=-]{32,}/g) || []) {
      if (/\d/.test(trecho) && /[A-Za-z]/.test(trecho)) {
        return 'Possível dado sensível (sequência longa semelhante a chave ou hash). Use apenas dados fictícios.';
      }
    }
    return null;
  }

  const ACOES_REVISAO = Object.freeze(['aprovar', 'rejeitar']);
  const LIMITE_JUSTIFICATIVA = Object.freeze([10, 500]);

  // Marco 4: regra da revisão humana simulada (R04/CA07). A revisão é registrada à parte
  // e NUNCA altera a decisão; item não autorizado não pode ser aprovado.
  function validarRevisao(entrada, acao, justificativa) {
    const {decisao} = classificar(entrada);
    const recusa = (codigo, motivo) => Object.freeze({aceita: false, codigo, motivo, decisao});
    if (!ACOES_REVISAO.includes(acao)) return recusa('acao_invalida', 'Selecione aprovar ou rejeitar.');
    const texto = String(justificativa ?? '').trim();
    const [min, max] = LIMITE_JUSTIFICATIVA;
    if (texto.length < min || texto.length > max) {
      return recusa('justificativa_invalida', `Justificativa obrigatória, entre ${min} e ${max} caracteres.`);
    }
    const segredo = detectarPossivelSegredo(texto);
    if (segredo) return recusa('possivel_segredo', segredo);
    if (acao === 'aprovar' && decisao === 'nao_autorizado') {
      return recusa('aprovacao_bloqueada', 'Item não autorizado não pode ser aprovado; a revisão humana não altera a classificação.');
    }
    return Object.freeze({aceita: true, codigo: 'ok', motivo: '', decisao});
  }

  globalThis.GovsafePolitica = Object.freeze({
    TAXONOMIA, DECISOES, ALERTA_EXTERNO, ACOES_REVISAO,
    classificar, validarRevisao, detectarPossivelSegredo
  });
})();
