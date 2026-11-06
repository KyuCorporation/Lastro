// Perguntas sugeridas na tela de consulta. Cobrem intents N1 do catálogo (SPEC §7).
// O CNPJ 99.999.999/0001-91 é o fornecedor fictício do seed (cena do ataque); o 99.000.001/0001-01 vem da
// fixture do TCE-PE (make demo). `{uf}` vira a primeira UF autorizada do usuário.

export const PERGUNTAS_SUGERIDAS = [
  "Qual o resumo de contratos e pagamentos do CNPJ 99.999.999/0001-91 em {uf}?",
  "Quais contratos do CNPJ 99.999.999/0001-91 vencem nos próximos 6 meses?",
  "O fornecedor 99.999.999/0001-91 tem sanção no CEIS ou no CNEP?",
  "Quanto o CNPJ 99.999.999/0001-91 recebeu em 2025?",
] as const;

export function sugestoesPara(ufs: string[]): string[] {
  const uf = ufs[0] ?? "PE";
  return PERGUNTAS_SUGERIDAS.map((p) => p.replace("{uf}", uf));
}
