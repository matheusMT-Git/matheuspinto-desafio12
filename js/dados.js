// Marco 3: cenários FICTÍCIOS iniciais (R09), compartilhados pelo app e pelos testes Node.
// Só entradas: a decisão é sempre calculada por js/politica.js, nunca armazenada.

(function () {
  const CENARIOS_INICIAIS = Object.freeze([
    {id: 1, finalidade: 'Resumo de boletim público de qualidade do ar', dado: 'publico', ambiente: 'desenvolvimento', autonomia: 'leitura', justificativa: 'Gerar resumo didático de dados já publicados.'},
    {id: 2, finalidade: 'Proposta de texto para FAQ de licenciamento', dado: 'publico', ambiente: 'desenvolvimento', autonomia: 'proposta', justificativa: 'Rascunho para revisão da equipe de comunicação.'},
    {id: 3, finalidade: 'Revisão de procedimento interno de protocolo', dado: 'interno', ambiente: 'homologacao', autonomia: 'proposta', justificativa: 'Sugerir melhorias de redação em documento interno fictício.'},
    {id: 4, finalidade: 'Análise de planilha de fornecedor externo', dado: 'externo', ambiente: 'desenvolvimento', autonomia: 'leitura', justificativa: 'Conferir colunas de planilha recebida de terceiro fictício.'},
    {id: 5, finalidade: 'Leitura de indicadores do painel de produção', dado: 'publico', ambiente: 'producao', autonomia: 'leitura', justificativa: 'Consultar indicadores públicos sem alterar nada.'},
    {id: 6, finalidade: 'Alterar configuração em servidor de produção', dado: 'interno', ambiente: 'producao', autonomia: 'edicao', justificativa: 'Ajuste de parâmetro solicitado em chamado fictício.'},
    {id: 7, finalidade: 'Rotacionar chave de acesso de integração', dado: 'credencial', ambiente: 'homologacao', autonomia: 'execucao', justificativa: 'Rotina periódica de troca de chave fictícia.'},
    {id: 8, finalidade: 'Excluir em lote registros de requerentes', dado: 'pessoal', ambiente: 'producao', autonomia: 'critica', justificativa: 'Limpeza de base solicitada em demanda fictícia.'}
  ].map((c) => Object.freeze(c)));

  globalThis.GovsafeDados = Object.freeze({CENARIOS_INICIAIS});
})();
