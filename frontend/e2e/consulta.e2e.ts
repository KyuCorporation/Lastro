// Passos da demo pela interface real, nas 5 telas do design: consulta, recibo, acesso, auditoria e fontes.
// Dados: seeds de demo e `ingest todas --offline` (make demo). Nada é simulado: VITE_CONSULTAS_SIMULADAS=false.

import { expect, test, type Page } from "@playwright/test";

async function entrarComo(page: Page, nome: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(`^${nome} ·`) }).click();
  await expect(page.getByRole("heading", { name: "Consulta inteligente" })).toBeVisible();
}

async function perguntar(page: Page, pergunta: string) {
  await page.getByLabel("Pergunta em linguagem natural").fill(pergunta);
  await page.getByRole("button", { name: "Consultar" }).click();
}

test("sem sessão, a tela protegida manda para o login", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Entrar no KYU" })).toBeVisible();
});

test("senha errada mostra a mensagem da API", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("ana@alfa.demo");
  await page.getByLabel("Senha").fill("errada");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toContainText("E-mail ou senha inválidos.");
});

test("registro sintético de teste aparece rotulado, com citação e recibo", async ({ page }) => {
  await entrarComo(page, "Ana");
  await expect(page.getByLabel("Estados autorizados: PE")).toBeVisible();

  await perguntar(page, "Quais contratos do CNPJ 99.999.999/0001-91 vencem nos próximos 6 meses?");

  const resposta = page.getByRole("region", { name: "Resposta com evidências" });
  await expect(resposta).toContainText("R$ 120.000,00");
  await expect(resposta).toContainText("99.999.999/0001-91");
  await expect(resposta.getByRole("note")).toContainText("registro sintético de teste"); // seed 020 é demo_sintetico
  await expect(resposta.getByText("cento e vinte mil reais")).toHaveClass(/sr-only/); // leitor de tela
  await expect(page.getByRole("heading", { name: "Resposta com evidências" })).toBeFocused(); // foco vai para a resposta

  const fontes = resposta.getByRole("region", { name: "Fontes citadas" });
  await expect(fontes.getByRole("listitem")).toHaveCount(1);
  await expect(fontes).toContainText("Registro sintético de teste");

  await resposta.getByRole("link", { name: "Ver evidências" }).click();
  await expect(page).toHaveURL(/\/recibos\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Recibo de evidências" })).toBeVisible();
});

test("contrato real do TCE-PE vem com link para a fonte oficial", async ({ page }) => {
  await entrarComo(page, "Ana");
  await perguntar(page, "Quais contratos do CNPJ 99.000.001/0001-01 vencem nos próximos 6 meses?");
  const resposta = page.getByRole("region", { name: "Resposta com evidências" });
  await expect(resposta).toContainText("R$ 1.250.000,00");
  await expect(resposta).toContainText("14/01/2027");
  await expect(resposta.getByRole("note")).toHaveCount(0); // não é dado sintético
  await expect(resposta.getByRole("link", { name: /Abrir na fonte oficial/ })).toHaveAttribute(
    "href",
    /^https:\/\/sistemas\.tcepe\.tc\.br\/DadosAbertos\/Contratos!json/,
  );
});

test("pedir outro estado aparece como acesso negado, sem número", async ({ page }) => {
  await entrarComo(page, "Ana");
  await perguntar(page, "Quanto o CNPJ 18.008.915/0001-09 recebeu em Alagoas?");
  const negado = page.getByRole("region", { name: "Acesso negado" });
  await expect(negado).toContainText("Você não tem acesso a dados de AL.");
  await expect(negado).not.toContainText(/\d/);
  await expect(page.getByRole("alert")).toHaveCount(0);
});

test("Ctrl+Enter envia a pergunta pelo teclado", async ({ page }) => {
  await entrarComo(page, "Ana");
  await page.getByLabel("Pergunta em linguagem natural").fill("O fornecedor 01.609.785/0001-67 tem sanção no CEIS?");
  await page.getByLabel("Pergunta em linguagem natural").press("Control+Enter");
  await expect(page.getByRole("region", { name: "Resposta com evidências" })).toContainText("sinal para investigar");
});

test("bia (AL) vê os contratos do PNCP de Alagoas", async ({ page }) => {
  await entrarComo(page, "Bia");
  await expect(page.getByLabel("Estados autorizados: AL")).toBeVisible();
  await perguntar(page, "Qual o resumo do fornecedor 18.008.915/0001-09?");
  const resposta = page.getByRole("region", { name: "Resposta com evidências" });
  await expect(resposta).toContainText("R$ 517.541,15");
  await expect(resposta.getByRole("link", { name: /Abrir na fonte oficial/ }).first()).toHaveAttribute(
    "href",
    /^https:\/\/pncp\.gov\.br\/app\/contratos\//,
  );
});

test("gestor não vê o formulário de consulta", async ({ page }) => {
  await entrarComo(page, "Gil");
  await expect(page.getByRole("note")).toContainText("não faz consultas em linguagem natural");
  await expect(page.getByLabel("Pergunta em linguagem natural")).toHaveCount(0);
});

test("sair encerra a sessão e a tela protegida volta a pedir login", async ({ page }) => {
  await entrarComo(page, "Ana");
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page.getByRole("heading", { name: "Entrar no KYU" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Entrar no KYU" })).toBeVisible();
});

test("recibo de evidências mostra os registros reais, o total e o selo", async ({ page }) => {
  await entrarComo(page, "Ana");
  await perguntar(page, "Quais contratos do CNPJ 99.000.001/0001-01 vencem nos próximos 6 meses?");
  const resposta = page.getByRole("region", { name: "Resposta com evidências" });
  await expect(resposta).toContainText("Valor total registrado: R$ 1.250.000,00");
  await expect(resposta).toContainText("Período considerado: próximos 180 dias");
  await expect(page.getByRole("region", { name: "Integridade da consulta" })).toContainText("Escopo: PE");
  await expect(page.getByRole("region", { name: "Integridade da consulta" })).toContainText("TCE-PE Dados Abertos");

  await resposta.getByRole("link", { name: "Ver evidências" }).click();
  await expect(page.getByRole("heading", { name: "Recibo de evidências" })).toBeVisible();
  await expect(page.getByText("R$ 1.250.000,00").first()).toBeVisible();
  await expect(page.getByText("1 registro relacionado")).toBeVisible();
  const linha = page.getByRole("table").getByRole("row").nth(1);
  await expect(linha).toContainText("TCE-PE Dados Abertos");
  await expect(linha.getByRole("link", { name: /Registro 01/ })).toHaveAttribute(
    "href",
    /^https:\/\/sistemas\.tcepe\.tc\.br\/DadosAbertos\//,
  );
  await expect(page.getByText(/Total reproduzível: .* = R\$ 1\.250\.000,00/)).toBeVisible();
  await expect(page.getByText(/^[0-9a-f]{64}$/)).toBeVisible(); // selo sha256 do recibo
});

test("teste de segurança vai para a API real e é bloqueado", async ({ page }) => {
  await entrarComo(page, "Ana");
  const cartao = page.getByRole("region", { name: "Teste de segurança" });
  await cartao.getByRole("button", { name: "Executar teste" }).click();
  await expect(cartao).toContainText("Bloqueada: Esse pedido está fora do que você pode consultar.");
});

test("auditoria lista as consultas da sessão, com filtro e link para o recibo", async ({ page }) => {
  await entrarComo(page, "Ana");
  await perguntar(page, "Qual o resumo do fornecedor 99.000.001/0001-01?");
  await expect(page.getByRole("region", { name: "Resposta com evidências" })).toBeVisible();
  await perguntar(page, "Quanto o CNPJ 18.008.915/0001-09 recebeu em Alagoas?");
  await expect(page.getByRole("region", { name: "Acesso negado" })).toBeVisible();

  await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: "Auditoria" }).click();
  await expect(page.getByRole("heading", { name: "Auditoria de consultas" })).toBeVisible();
  const tabela = page.getByRole("table");
  await expect(tabela.getByRole("row").nth(1)).toContainText("Bloqueada"); // a mais recente primeiro
  await expect(tabela.getByRole("row").nth(2)).toContainText("Respondida");

  await page.getByRole("button", { name: "Bloqueadas" }).click();
  await expect(tabela).not.toContainText("Respondida");
  await page.getByRole("button", { name: "Respondidas" }).click();
  await tabela.getByRole("link", { name: "Ver recibo" }).first().click();
  await expect(page.getByRole("heading", { name: "Recibo de evidências" })).toBeVisible();
});

test("auditor vê as consultas do cliente e não pergunta", async ({ page }) => {
  await entrarComo(page, "Caio");
  await expect(page.getByLabel("Pergunta em linguagem natural")).toHaveCount(0);
  await page.getByRole("link", { name: "Auditoria" }).click();
  await expect(page.getByText(/Consultas de todo o cliente/)).toBeVisible();
  await expect(page.getByRole("table")).toBeVisible();
});

test("acesso mostra a sessão real e a matriz; gestor não tem Auditoria no menu", async ({ page }) => {
  await entrarComo(page, "Bia");
  await page.getByRole("link", { name: "Acesso" }).click();
  await expect(page.getByRole("heading", { name: "Controle de acesso por perfil" })).toBeVisible();
  await expect(page.getByRole("region", { name: "Sessão atual" })).toContainText("Estado autorizado: Alagoas (AL)");
  await expect(page.getByRole("rowheader", { name: /Analista de risco/ })).toContainText("(você)");

  await page.getByRole("button", { name: "Sair" }).click();
  await entrarComo(page, "Gil");
  const menu = page.getByRole("navigation", { name: "Principal" });
  await expect(menu.getByRole("link", { name: "Auditoria" })).toHaveCount(0);
});

test("fontes mostra a última coleta real de cada fonte (GET /fontes)", async ({ page }) => {
  await entrarComo(page, "Ana");
  await page.getByRole("link", { name: "Fontes e catálogo" }).click();
  await expect(page.getByRole("heading", { name: "Fonte e catálogo de dados" })).toBeVisible();
  const tabela = page.getByRole("table", { name: /Fontes integradas/ });
  await expect(tabela.getByRole("row", { name: /Cadastro de Empresas Inidôneas/ })).toContainText("Coletada");
  await expect(tabela.getByRole("row", { name: /Portal Nacional de Contratações/ })).toContainText("Coletada");
  await expect(page.getByText(/A confirmar|A validar|previsto/)).toHaveCount(0);
});

test("nenhuma tela mostra aviso de dados fictícios", async ({ page }) => {
  await entrarComo(page, "Ana");
  for (const tela of ["Consulta", "Fontes e catálogo", "Acesso", "Auditoria"]) {
    await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: tela }).click();
    await expect(page.getByText(/fictíci|Demonstração ·|não representa consulta oficial/i)).toHaveCount(0);
  }
});

test("cores e marca da KYU estão aplicadas", async ({ page }) => {
  await entrarComo(page, "Ana");
  const lateral = page.locator("aside");
  await expect(lateral).toHaveCSS("background-color", "rgb(43, 26, 20)"); // #2B1A14
  await expect(page.getByRole("button", { name: "Consultar" })).toHaveCSS("background-color", "rgb(181, 71, 29)"); // #B5471D
  await expect(lateral.getByText("KYU")).toBeVisible();
  await expect(lateral.locator("svg rect")).toHaveCount(1); // marca: losango
});
