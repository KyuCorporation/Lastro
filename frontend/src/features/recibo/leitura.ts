// Leituras do recibo para as telas. Tudo vem do backend: aqui só se escolhe e se formata.

import type { ConteudoRecibo } from "../../api/types";
import { dataCurta, moeda } from "../../lib/formato";

export interface ValorDestacado {
  marcador: string;
  valor: string;
  origem: string;
}

// O valor de cabeçalho é o total principal de cada consulta (origem gravada no recibo pelo backend).
const PREFERENCIA_ORIGEM = [
  "sum(contratos.valor_global)",
  "sum(valor_global)",
  "sum(valor_global) vigentes",
  "sum(pagamentos.valor)",
];

/** Valores em reais que o recibo registrou, na ordem dos marcadores. */
export function valoresMoeda(conteudo: ConteudoRecibo): ValorDestacado[] {
  return Object.entries(conteudo.valores ?? {})
    .filter(([, v]) => v.tipo === "moeda")
    .sort(([a], [b]) => Number(a.slice(1)) - Number(b.slice(1)))
    .map(([marcador, v]) => ({ marcador, valor: v.valor, origem: v.origem ?? "" }));
}

export function valorPrincipal(conteudo: ConteudoRecibo): ValorDestacado | null {
  const valores = valoresMoeda(conteudo);
  for (const origem of PREFERENCIA_ORIGEM) {
    const achado = valores.find((v) => v.origem === origem);
    if (achado) return achado;
  }
  return valores[0] ?? null;
}

/** "Período considerado" do resumo da consulta, a partir dos parâmetros efetivos. */
export function periodo(conteudo: ConteudoRecibo): string | null {
  const p = conteudo.execucao.parametros_efetivos;
  if (typeof p.data_inicio === "string" && typeof p.data_fim === "string") {
    return `${dataCurta(p.data_inicio)} a ${dataCurta(p.data_fim)}`;
  }
  if (typeof p.dias === "number" && typeof p.hoje === "string") {
    return `próximos ${p.dias} dias a partir de ${dataCurta(p.hoje)}`;
  }
  if (typeof p.hoje === "string" && conteudo.execucao.consulta_catalogo.startsWith("contratos_vigentes")) {
    return `contratos vigentes em ${dataCurta(p.hoje)}`;
  }
  if (typeof p.hoje === "string") return `todo o histórico carregado até ${dataCurta(p.hoje)}`;
  return null;
}

export function consultouSancoes(conteudo: ConteudoRecibo): boolean {
  return conteudo.execucao.consulta_catalogo.startsWith("sancoes_fornecedor");
}

export function temDadoSintetico(conteudo: ConteudoRecibo): boolean {
  return conteudo.fontes.some((f) => f.sintetico) || conteudo.linhas.some((l) => l.fonte_id === "demo_sintetico");
}

export function nomesFontes(conteudo: ConteudoRecibo): string[] {
  return [...new Set(conteudo.fontes.map((f) => f.nome))];
}

export { moeda };
