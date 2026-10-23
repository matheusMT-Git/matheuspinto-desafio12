// Marco 6: testes E2E (Playwright) — numeração segue docs/MAPA_REQUISITOS_TESTES.md.
// Executar: npm run test:e2e   (cada teste roda em contexto novo, com localStorage vazio)
import {test as base, expect} from '@playwright/test';
import {readFile} from 'node:fs/promises';

// Fixture automática: bloqueia e conta qualquer requisição fora de 127.0.0.1 e
// coleta erros de console/página. Todo teste falha se houver algum (R08/CA09).
const test = base.extend({
  vigilancia: [async ({page}, use, testInfo) => {
    const externas = [];
    const erros = [];
    await page.route('**/*', (route) => {
      const url = new URL(route.request().url());
      if (url.hostname === '127.0.0.1') return route.continue();
      externas.push(url.href);
      return route.abort();
    });
    page.on('console', (msg) => { if (msg.type() === 'error') erros.push(msg.text()); });
    page.on('pageerror', (erro) => erros.push(erro.message));
    await use({externas, erros});
    // Evidência: print final de cada teste em evidencias/prints/<projeto>/
    const nome = testInfo.title.slice(0, 2) + '-' + testInfo.title.slice(3, 40).replace(/[^a-z0-9]+/gi, '-').replace(/-$/, '');
    await page.screenshot({path: `evidencias/prints/${testInfo.project.name}/${nome}.png`, fullPage: true}).catch(() => {});
    expect(externas, 'requisições externas').toEqual([]);
    expect(erros, 'erros de JavaScript no console').toEqual([]);
  }, {auto: true}]
});

const tabela = (page) => page.locator('#tabela-cenarios tr');
const linha = (page, id) => page.locator('#tabela-cenarios tr').filter({has: page.locator('td:first-child', {hasText: new RegExp(`^${id}$`)})});

async function esperarTotais(page, [total, permitido, condicionado, naoAutorizado]) {
  await expect(page.locator('#total-geral')).toHaveText(String(total));
  await expect(page.locator('#total-permitido')).toHaveText(String(permitido));
  await expect(page.locator('#total-condicionado')).toHaveText(String(condicionado));
  await expect(page.locator('#total-nao-autorizado')).toHaveText(String(naoAutorizado));
}

async function cadastrar(page, {finalidade, dado, ambiente, autonomia, justificativa}) {
  await page.getByLabel('Finalidade', {exact: true}).fill(finalidade);
  await page.getByLabel('Tipo de dado').selectOption(dado);
  await page.getByLabel('Ambiente', {exact: true}).selectOption(ambiente);
  await page.getByLabel('Autonomia', {exact: true}).selectOption(autonomia);
  await page.getByLabel('Justificativa', {exact: true}).fill(justificativa);
  await page.getByRole('button', {name: 'Classificar e salvar'}).click();
}

const EXTERNO = {
  finalidade: 'Resumir parecer de consultoria fictícia',
  dado: 'externo', ambiente: 'desenvolvimento', autonomia: 'leitura',
  justificativa: 'Teste E2E com documento externo inventado.'
};

test.beforeEach(async ({page}) => {
  await page.goto('/');
});

test('01 dashboard: 8 cenários, totais consistentes e aviso de não homologado (CA01, R10)', async ({page}) => {
  await expect(tabela(page)).toHaveCount(8);
  await esperarTotais(page, [8, 2, 3, 3]);
  await expect(page.getByRole('note')).toContainText('NÃO é sistema institucional homologado');
  await expect(page.locator('#contador')).toHaveText('Exibindo 8 de 8 cenários.');
});

test('02 busca: sem acento, sem diferenciar maiúsculas, e estado vazio', async ({page}) => {
  const busca = page.getByLabel('Buscar na finalidade ou justificativa');
  await busca.fill('PRODUCAO');
  await expect(tabela(page)).toHaveCount(2);
  await expect(linha(page, 5)).toBeVisible();
  await expect(linha(page, 6)).toBeVisible();
  await busca.fill('termo-que-nao-existe');
  await expect(page.locator('#tabela-cenarios .estado-vazio')).toHaveText('Nenhum cenário corresponde ao filtro.');
  await expect(page.locator('#contador')).toHaveText('Exibindo 0 de 8 cenários.');
});

test('03 filtro por decisão afeta só a tabela', async ({page}) => {
  await page.getByLabel('Decisão', {exact: true}).selectOption('nao_autorizado');
  await expect(tabela(page)).toHaveCount(3);
  await expect(page.locator('#tabela-cenarios .selo')).toHaveText(['Não autorizado', 'Não autorizado', 'Não autorizado']);
  await esperarTotais(page, [8, 2, 3, 3]);
});

test('04 cadastro, validação e persistência após F5 (CA05, CA06)', async ({page}) => {
  await page.getByRole('button', {name: 'Classificar e salvar'}).click();
  await expect(page.locator('#erro-finalidade')).toContainText('Informe entre 5 e 120');
  await expect(page.getByLabel('Finalidade', {exact: true})).toBeFocused();

  await cadastrar(page, {...EXTERNO, finalidade: 'Consultar requerente 123.456.789-09'});
  await expect(page.locator('#erro-finalidade')).toContainText('padrão de CPF');
  await esperarTotais(page, [8, 2, 3, 3]);

  await cadastrar(page, EXTERNO);
  await expect(page.locator('#mensagem-cadastro')).toContainText('Cenário #9 classificado como Condicionado (R4)');
  await expect(page.locator('#mensagem-cadastro')).toContainText('não possui autoridade');
  await esperarTotais(page, [9, 2, 4, 3]);

  await page.reload();
  await esperarTotais(page, [9, 2, 4, 3]);
  await expect(linha(page, 9)).toContainText(EXTERNO.finalidade);
  await expect(page.locator('#lista-auditoria li').first()).toContainText('Cenário #9 cadastrado');
});

test('05 revisão humana: não altera decisão e item proibido não vira aprovado (CA07)', async ({page}) => {
  await page.getByRole('button', {name: 'Revisar cenário #3'}).click();
  const dialogo = page.getByRole('dialog');
  await expect(dialogo).toContainText('Decisão do motor: Condicionado');
  await page.locator('#revisao-aprovar').check();
  await dialogo.getByRole('button', {name: 'Registrar revisão'}).click();
  await expect(page.locator('#erro-revisao')).toContainText('Justificativa obrigatória');
  await dialogo.getByLabel('Justificativa da revisão (obrigatória)').fill('Proposta revisada pela equipe fictícia.');
  await dialogo.getByRole('button', {name: 'Registrar revisão'}).click();
  await expect(dialogo).toBeHidden();
  await expect(linha(page, 3).locator('.selo')).toHaveText('Condicionado');
  await expect(linha(page, 3).locator('td').nth(6)).toHaveText('Aprovado');
  await expect(page.getByRole('button', {name: 'Revisar cenário #3'})).toBeFocused();

  await page.getByRole('button', {name: 'Revisar cenário #7'}).click();
  await expect(page.locator('#revisao-aprovar')).toBeDisabled();
  await expect(page.locator('#revisao-bloqueio')).toContainText('não pode ser aprovado');
  // Burla deliberada: reativa o botão pelo "DevTools" e tenta aprovar.
  await page.evaluate(() => {
    const aprovar = document.getElementById('revisao-aprovar');
    aprovar.disabled = false;
    aprovar.checked = true;
  });
  await dialogo.getByLabel('Justificativa da revisão (obrigatória)').fill('Tentativa de burlar a regra pelo DevTools.');
  await dialogo.getByRole('button', {name: 'Registrar revisão'}).click();
  await expect(page.locator('#erro-revisao')).toContainText('não pode ser aprovado');
  await page.keyboard.press('Escape');
  await expect(linha(page, 7).locator('td').nth(6)).toHaveText('Pendente');
  await expect(page.locator('#lista-auditoria li').first()).toContainText('Aprovação bloqueada');

  await page.reload();
  await expect(linha(page, 3).locator('td').nth(6)).toHaveText('Aprovado');
  await expect(linha(page, 7).locator('td').nth(6)).toHaveText('Pendente');
});

test('06 exportações: CSV com cabeçalho e dados, JSON com eventos (CA08)', async ({page}) => {
  await cadastrar(page, EXTERNO);

  const [csv] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', {name: 'Exportar matriz (CSV)'}).click()]);
  expect(csv.suggestedFilename()).toMatch(/^govsafe360-matriz-\d{4}-\d{2}-\d{2}\.csv$/);
  const bytes = await readFile(await csv.path());
  expect([...bytes.subarray(0, 3)]).toEqual([0xEF, 0xBB, 0xBF]);
  const linhasCsv = bytes.toString('utf8').slice(1).trim().split('\r\n');
  expect(linhasCsv).toHaveLength(10);
  expect(linhasCsv[0]).toBe('"id";"finalidade";"dado";"ambiente";"autonomia";"decisao";"regra";"motivo";"alertas";"revisao_status";"revisao_justificativa";"revisao_data"');
  expect(linhasCsv[7]).toContain('"credencial";"homologacao";"execucao";"nao_autorizado";"R1"');
  expect(linhasCsv[9]).toContain('"externo";"desenvolvimento";"leitura";"condicionado";"R4"');

  const [json] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', {name: 'Exportar auditoria (JSON)'}).click()]);
  expect(json.suggestedFilename()).toMatch(/^govsafe360-auditoria-\d{4}-\d{2}-\d{2}\.json$/);
  const auditoria = JSON.parse(await readFile(await json.path(), 'utf8'));
  expect(auditoria.sistema).toContain('NÃO homologado');
  expect(auditoria.total_eventos).toBe(auditoria.eventos.length);
  expect(auditoria.eventos.map((e) => e.tipo)).toEqual(['cenario_cadastrado', 'exportacao_csv', 'exportacao_json']);
  for (const e of auditoria.eventos) {
    expect(Number.isInteger(e.seq) && e.data && e.resumo).toBeTruthy();
  }
});

test('07 responsividade: sem rolagem horizontal da página; tabela rola no .table-wrap (CA10)', async ({page}, testInfo) => {
  const medir = () => page.evaluate(() => {
    const wrap = document.querySelector('.table-wrap');
    return {
      pagina: document.documentElement.scrollWidth,
      janela: window.innerWidth,
      wrapRola: wrap.scrollWidth > wrap.clientWidth
    };
  });
  let m = await medir();
  expect(m.pagina).toBeLessThanOrEqual(m.janela + 2);
  if (testInfo.project.name === 'mobile') {
    expect(m.janela).toBe(390);
    expect(m.wrapRola).toBe(true);
  }
  await page.getByRole('button', {name: 'Revisar cenário #1'}).click();
  const caixa = await page.getByRole('dialog').boundingBox();
  expect(caixa.x).toBeGreaterThanOrEqual(0);
  expect(caixa.x + caixa.width).toBeLessThanOrEqual(m.janela);
  m = await medir();
  expect(m.pagina).toBeLessThanOrEqual(m.janela + 2);
});

test('08 produção sem execução autônoma: não autorizado e não aprovável', async ({page}) => {
  await cadastrar(page, {
    finalidade: 'Reiniciar serviço de produção fictício',
    dado: 'interno', ambiente: 'producao', autonomia: 'execucao',
    justificativa: 'Teste E2E de execução em produção.'
  });
  await expect(page.locator('#mensagem-cadastro')).toContainText('Não autorizado (R2)');
  await expect(linha(page, 9).locator('.selo')).toHaveText('Não autorizado');
  await esperarTotais(page, [9, 2, 3, 4]);
  await page.getByRole('button', {name: 'Revisar cenário #9'}).click();
  await expect(page.locator('#revisao-aprovar')).toBeDisabled();
});

test('09 funciona sem internet depois de carregado (R08, CA09)', async ({page, context}) => {
  await context.setOffline(true);
  await cadastrar(page, EXTERNO);
  await esperarTotais(page, [9, 2, 4, 3]);
  await page.getByLabel('Decisão', {exact: true}).selectOption('condicionado');
  await expect(tabela(page)).toHaveCount(4);
  const [csv] = await Promise.all([page.waitForEvent('download'), page.getByRole('button', {name: 'Exportar matriz (CSV)'}).click()]);
  expect(csv.suggestedFilename()).toMatch(/\.csv$/);
  await context.setOffline(false);
  // A fixture `vigilancia` confere ao final: zero requisições externas e console sem erros.
});

test('10 limpar dados: confirmação real com Cancelar e OK', async ({page}) => {
  await cadastrar(page, EXTERNO);
  await esperarTotais(page, [9, 2, 4, 3]);
  const limpar = page.getByRole('button', {name: 'Limpar dados locais'});

  page.once('dialog', (d) => d.dismiss());
  await limpar.click();
  await esperarTotais(page, [9, 2, 4, 3]);

  let mensagem = '';
  page.once('dialog', (d) => { mensagem = d.message(); d.accept(); });
  await limpar.click();
  expect(mensagem).toContain('restaurar os 8 cenários fictícios iniciais');
  await esperarTotais(page, [8, 2, 3, 3]);
  await page.reload();
  await esperarTotais(page, [8, 2, 3, 3]);
  await expect(page.locator('#lista-auditoria li')).toHaveCount(1);
  await expect(page.locator('#lista-auditoria li').first()).toContainText('Dados limpos');
});
