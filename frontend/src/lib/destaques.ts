// Quebra o texto da resposta em trechos para destacar valores e ligar as marcas de citação.
// O texto já chega com os números inseridos pelo backend (verificador, SPEC §8.3): aqui só se formata.

import { moedaPorExtenso } from "./extenso";

export type Trecho =
  | { tipo: "texto"; texto: string }
  | { tipo: "moeda"; texto: string; falado: string }
  | { tipo: "data"; texto: string; falado: string }
  | { tipo: "numero"; texto: string }
  | { tipo: "cnpj"; texto: string }
  | { tipo: "citacao"; texto: string; n: number };

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

// Ordem importa: CNPJ, moeda e data antes de número solto; citação "[n]".
const PADRAO = new RegExp(
  [
    String.raw`(?<cnpj>\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b)`,
    String.raw`(?<moeda>R\$\s?\d{1,3}(?:\.\d{3})*(?:,\d{2})?)`,
    String.raw`(?<data>\b\d{2}/\d{2}/\d{4}\b)`,
    String.raw`(?<citacao>\[(?<n>\d{1,3})\])`,
    String.raw`(?<numero>\b\d+(?:[.,]\d+)*%?)`,
  ].join("|"),
  "g",
);

function dataFalada(texto: string): string {
  const [dia, mes, ano] = texto.split("/").map(Number);
  return MESES[mes - 1] ? `${dia} de ${MESES[mes - 1]} de ${ano}` : texto;
}

export function dividirEmTrechos(texto: string): Trecho[] {
  const trechos: Trecho[] = [];
  let ultimo = 0;
  for (const achado of texto.matchAll(PADRAO)) {
    const inicio = achado.index ?? 0;
    if (inicio > ultimo) trechos.push({ tipo: "texto", texto: texto.slice(ultimo, inicio) });
    const g = achado.groups ?? {};
    if (g.cnpj) trechos.push({ tipo: "cnpj", texto: g.cnpj });
    else if (g.moeda) trechos.push({ tipo: "moeda", texto: g.moeda, falado: moedaPorExtenso(g.moeda) });
    else if (g.data) trechos.push({ tipo: "data", texto: g.data, falado: dataFalada(g.data) });
    else if (g.citacao) trechos.push({ tipo: "citacao", texto: g.citacao, n: Number(g.n) });
    else trechos.push({ tipo: "numero", texto: g.numero });
    ultimo = inicio + achado[0].length;
  }
  if (ultimo < texto.length) trechos.push({ tipo: "texto", texto: texto.slice(ultimo) });
  return trechos;
}
