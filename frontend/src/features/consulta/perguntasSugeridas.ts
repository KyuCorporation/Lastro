// Perguntas sugeridas na tela de consulta, só com dados reais da base: contratos do PNCP (AL) e sanções do
// CEIS/CNEP (nacionais). Cada usuário vê as que cabem no próprio escopo.

const SANCOES = [
  "A empresa 20.217.208/0001-74 tem sanção no CEIS ou no CNEP?",
  "A empresa 26.852.688/0001-21 tem alguma sanção no CEIS ou no CNEP?",
];

const POR_UF: Record<string, string[]> = {
  AL: [
    "Qual o resumo do fornecedor 21.162.446/0001-92?",
    "Quais contratos vigentes o CNPJ 18.008.915/0001-09 tem?",
  ],
};

export function sugestoesPara(ufs: string[]): string[] {
  return [...ufs.flatMap((uf) => POR_UF[uf] ?? []), ...SANCOES];
}
