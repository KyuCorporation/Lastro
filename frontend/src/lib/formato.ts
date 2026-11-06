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
  demo_sintetico: "Registro sintético de teste",
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

/** "2027-01-14" ou ISO com hora → "14/01/2027" (sem mudar o dia por fuso). */
export function dataCurta(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : iso;
}

/** Hora local de Recife, "08:12". */
export function hora(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit", timeZone: "America/Recife" });
}

/** String decimal da API ("1250000.00") → "R$ 1.250.000,00". */
export function moeda(decimal: string): string {
  const n = Number(decimal);
  if (!Number.isFinite(n)) return decimal;
  // Espaço comum no lugar do não separável: o mesmo texto que o backend escreve nas respostas.
  return n.toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: 2 }).replace(/\s/g, " ");
}
