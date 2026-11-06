// Capturas das 5 telas, no tamanho dos mockups do design, para comparar lado a lado.
// Uso (com make demo de pé): npx tsx e2e/capturas.ts <pasta>   (E2E_CANAL=msedge sem Chrome)

import { chromium } from "@playwright/test";

const BASE = process.env.E2E_URL ?? "http://localhost:5173";
const pasta = process.argv[2] ?? "capturas";

const navegador = await chromium.launch({ channel: process.env.E2E_CANAL ?? "chrome" });
const page = await navegador.newPage({ viewport: { width: 1573, height: 957 }, locale: "pt-BR" });

await page.goto(`${BASE}/login`);
await page.screenshot({ path: `${pasta}/00-login.png` });
await page.getByRole("button", { name: /^Ana ·/ }).click();
await page.getByRole("heading", { name: "Consulta inteligente" }).waitFor();

await page.getByLabel("Pergunta em linguagem natural").fill("Faça um resumo do fornecedor 99.000.001/0001-01");
await page.getByRole("button", { name: "Consultar" }).click();
await page.getByText(/Valor total registrado/).waitFor();
await page.screenshot({ path: `${pasta}/01-consulta.png`, fullPage: true });

await page.getByRole("link", { name: "Ver evidências" }).click();
await page.getByRole("table").waitFor();
await page.screenshot({ path: `${pasta}/02-recibo.png`, fullPage: true });

for (const [rotulo, arquivo] of [
  ["Acesso", "03-acesso"],
  ["Auditoria", "04-auditoria"],
  ["Fontes e catálogo", "05-fontes"],
] as const) {
  await page.getByRole("navigation", { name: "Principal" }).getByRole("link", { name: rotulo }).click();
  await page.waitForLoadState("networkidle");
  if (rotulo === "Auditoria") await page.getByRole("table").waitFor();
  await page.screenshot({ path: `${pasta}/${arquivo}.png`, fullPage: true });
}

await navegador.close();
