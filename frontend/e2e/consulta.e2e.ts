// Passo da demo pela interface real (SPEC §12): login → pergunta → resposta com números, citações e recibo.
// Dados: seeds de demo e `ingest todas --offline` (make demo). Nada é simulado: VITE_CONSULTAS_SIMULADAS=false.

import { expect, test, type Page } from "@playwright/test";

async function entrarComo(page: Page, nome: string) {
  await page.goto("/login");
  await page.getByRole("button", { name: new RegExp(`^${nome} ·`) }).click();
  await expect(page.getByRole("heading", { name: "Consulta" })).toBeVisible();
}

async function perguntar(page: Page, pergunta: string) {
  await page.getByLabel("Sua pergunta").fill(pergunta);
  await page.getByRole("button", { name: "Perguntar" }).click();
}

test("sem sessão, a tela protegida manda para o login", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Entrar no Lastro" })).toBeVisible();
});

test("senha errada mostra a mensagem da API", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("E-mail").fill("ana@alfa.demo");
  await page.getByLabel("Senha").fill("errada");
  await page.getByRole("button", { name: "Entrar" }).click();
  await expect(page.getByRole("alert")).toContainText("E-mail ou senha inválidos.");
});

test("ana pergunta pela sugestão e recebe resposta com selo sintético, citação e recibo", async ({ page }) => {
  await entrarComo(page, "Ana");
  await expect(page.getByLabel("Estados autorizados: PE")).toBeVisible();

  await page.getByRole("button", { name: /vencem nos próximos 6 meses/ }).click();
  await page.getByRole("button", { name: "Perguntar" }).click();

  const resposta = page.getByRole("region", { name: "Resposta" });
  await expect(resposta).toContainText("R$ 120.000,00");
  await expect(resposta).toContainText("99.999.999/0001-91");
  await expect(resposta.getByRole("note")).toContainText("dado sintético"); // seed 020 é demo_sintetico
  await expect(resposta.getByText("cento e vinte mil reais")).toHaveClass(/sr-only/); // leitor de tela
  await expect(page.getByRole("heading", { name: "Resposta" })).toBeFocused(); // foco vai para a resposta

  const fontes = resposta.getByRole("region", { name: "Fontes citadas" });
  await expect(fontes.getByRole("listitem")).toHaveCount(1);
  await expect(fontes).toContainText("Dado sintético de demonstração");

  await resposta.getByRole("link", { name: "Ver recibo" }).click();
  await expect(page).toHaveURL(/\/recibos\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Recibo" })).toBeVisible();
});

test("contrato real do TCE-PE vem com link para a fonte oficial", async ({ page }) => {
  await entrarComo(page, "Ana");
  await perguntar(page, "Quais contratos do CNPJ 99.000.001/0001-01 vencem nos próximos 6 meses?");
  const resposta = page.getByRole("region", { name: "Resposta" });
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
  await page.getByLabel("Sua pergunta").fill("O fornecedor 01.609.785/0001-67 tem sanção no CEIS?");
  await page.getByLabel("Sua pergunta").press("Control+Enter");
  await expect(page.getByRole("region", { name: "Resposta" })).toContainText("sinal para investigar");
});

test("bia (AL) vê os contratos do PNCP de Alagoas", async ({ page }) => {
  await entrarComo(page, "Bia");
  await expect(page.getByLabel("Estados autorizados: AL")).toBeVisible();
  await perguntar(page, "Qual o resumo do fornecedor 18.008.915/0001-09?");
  const resposta = page.getByRole("region", { name: "Resposta" });
  await expect(resposta).toContainText("R$ 517.541,15");
  await expect(resposta.getByRole("link", { name: /Abrir na fonte oficial/ }).first()).toHaveAttribute(
    "href",
    /^https:\/\/pncp\.gov\.br\/app\/contratos\//,
  );
});

test("gestor não vê o formulário de consulta", async ({ page }) => {
  await entrarComo(page, "Gil");
  await expect(page.getByRole("note")).toContainText("não faz consultas em linguagem natural");
  await expect(page.getByLabel("Sua pergunta")).toHaveCount(0);
});

test("sair encerra a sessão e a tela protegida volta a pedir login", async ({ page }) => {
  await entrarComo(page, "Ana");
  await page.getByRole("button", { name: "Sair" }).click();
  await expect(page.getByRole("heading", { name: "Entrar no Lastro" })).toBeVisible();
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Entrar no Lastro" })).toBeVisible();
});
