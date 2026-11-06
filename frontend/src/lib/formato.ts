// Formatação só na interface (AGENTS.md §7): a API manda ISO 8601; a tela mostra dd/mm/aaaa.

export function dataHora(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short", timeZone: "America/Recife" });
}

/** Nomes das fontes para exibição (fontes.nome no banco). */
const NOMES_FONTES: Record<string, string> = {
  pe_portal: "TCE-PE Dados Abertos",
  pncp: "PNCP",
  ceis: "CEIS",
  cnep: "CNEP",
  receita_qsa: "Quadro societário (Receita)",
  demo_sintetico: "Dado sintético de demonstração",
};

export function nomeFonte(fonteId: string): string {
  return NOMES_FONTES[fonteId] ?? fonteId;
}

const NOMES_TABELAS: Record<string, string> = {
  contratos: "Contrato",
  pagamentos: "Pagamento",
  sancoes: "Sanção",
  sinais: "Sinal para investigar",
  socios: "Sócio",
};

export function nomeTabela(tabela: string): string {
  return NOMES_TABELAS[tabela] ?? tabela;
}
