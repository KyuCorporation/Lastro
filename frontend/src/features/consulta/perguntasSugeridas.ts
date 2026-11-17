// Perguntas sugeridas na tela de consulta, só com fornecedores reais da base. Cada usuário vê as do próprio
// escopo e, depois, as de sanção (CEIS/CNEP são nacionais).
//
// PE: amostra real do TCE-PE (data/fixtures/pe_portal/amostra, coletada em 15/11/2026), com contratos vigentes.
// Não há sugestão de busca por objeto em PE: na API do TCE-PE o campo Objeto traz só a categoria do contrato.
// AL: contratos do PNCP. Trocar pelos CNPJs da carga completa quando ela for feita.

export const POR_UF: Record<string, string[]> = {
  PE: [
    "Qual o resumo do fornecedor 17.238.558/0001-02?",
    "Quais contratos do CNPJ 17.238.558/0001-02 vencem nos próximos 6 meses?",
    "Quais contratos vigentes o CNPJ 19.452.240/0001-55 tem?",
    "Quais órgãos mais contratam o CNPJ 05.342.580/0001-19?",
  ],
  AL: [
    "Qual o resumo do fornecedor 21.162.446/0001-92?",
    "Quais contratos vigentes o CNPJ 18.008.915/0001-09 tem?",
  ],
};

export const SANCOES = [
  "A empresa 20.217.208/0001-74 tem sanção no CEIS ou no CNEP?",
  "A empresa 26.852.688/0001-21 tem alguma sanção no CEIS ou no CNEP?",
];

export function sugestoesPara(ufs: string[]): string[] {
  return [...ufs.flatMap((uf) => POR_UF[uf] ?? []), ...SANCOES];
}
