import { defineConfig } from "@playwright/test";

// E2E com navegador real contra o sistema de pé (make demo): web em E2E_URL e a API que ela usa.
// Usa o Google Chrome instalado na máquina (channel "chrome"); não baixa navegador.
export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.e2e\.ts/,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1, // um usuário por vez: o limite de 30 consultas por minuto vale por usuário
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: process.env.E2E_URL ?? "http://localhost:5173",
    channel: "chrome",
    headless: true,
    locale: "pt-BR",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
