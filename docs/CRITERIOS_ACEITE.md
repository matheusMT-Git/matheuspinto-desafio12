# Critérios de aceite e evidência
CA01: dashboard exibe oito registros iniciais e totais consistentes.
CA02: credencial -> não autorizado, sem pedir/token armazenar segredo.
CA03: produção -> condicionado ou não autorizado segundo criticidade.
CA04: ação crítica -> não autorizado.
CA05: dado externo -> condicionado e sinaliza ausência de autoridade instrucional.
CA06: novo cenário sintético persiste após F5.
CA07: revisão humana fictícia exige justificativa; não pode converter não autorizado em permitido automaticamente.
CA08: CSV baixa com cabeçalhos e dados; JSON de auditoria possui eventos.
CA09: botões funcionam sem internet; console sem erros de JavaScript.
CA10: interface utilizável em viewport de 390px com document.documentElement.scrollWidth <= window.innerWidth + 2; rolagem da tabela fica dentro de .table-wrap.
CA11: `CLAUDE.md` não é tratado como barreira de execução; controles estão na lógica do sistema e permissões reais do Claude Code.
