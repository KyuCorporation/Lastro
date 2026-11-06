// Valores por extenso para leitor de tela (SPEC §12): "R$ 1.250.000,00" → "um milhão duzentos e cinquenta mil reais".

const UNIDADES = [
  "zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove",
  "dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove",
];
const DEZENAS = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"];
const CENTENAS = [
  "", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos",
  "seiscentos", "setecentos", "oitocentos", "novecentos",
];
const ESCALAS: [singular: string, plural: string][] = [
  ["", ""],
  ["mil", "mil"],
  ["milhão", "milhões"],
  ["bilhão", "bilhões"],
  ["trilhão", "trilhões"],
];

function ate999(n: number): string {
  if (n === 100) return "cem";
  const c = Math.floor(n / 100);
  const resto = n % 100;
  const partes: string[] = [];
  if (c) partes.push(CENTENAS[c]);
  if (resto) {
    if (resto < 20) partes.push(UNIDADES[resto]);
    else {
      const d = Math.floor(resto / 10);
      const u = resto % 10;
      partes.push(u ? `${DEZENAS[d]} e ${UNIDADES[u]}` : DEZENAS[d]);
    }
  }
  return partes.join(" e ");
}

/** Inteiro não negativo por extenso (até trilhões). */
export function inteiroPorExtenso(n: number): string {
  if (!Number.isSafeInteger(n) || n < 0) return String(n);
  if (n === 0) return "zero";
  const grupos: number[] = [];
  for (let resto = n; resto > 0; resto = Math.floor(resto / 1000)) grupos.push(resto % 1000);
  if (grupos.length > ESCALAS.length) return String(n);

  const partes: string[] = [];
  for (let i = grupos.length - 1; i >= 0; i--) {
    const g = grupos[i];
    if (!g) continue;
    const [singular, plural] = ESCALAS[i];
    if (i === 1) partes.push(g === 1 ? "mil" : `${ate999(g)} mil`);
    else partes.push(i === 0 ? ate999(g) : `${ate999(g)} ${g === 1 ? singular : plural}`);
  }
  // "e" antes do último grupo quando ele é < 100 ou centena redonda: "mil e quinhentos", "dois mil e dez".
  const ultimo = grupos[0];
  if (partes.length > 1 && ultimo && (ultimo < 100 || ultimo % 100 === 0)) {
    const fim = partes.pop()!;
    return `${partes.join(" ")} e ${fim}`;
  }
  return partes.join(" ");
}

/** "1234.56" ou "1.234,56" → "mil duzentos e trinta e quatro reais e cinquenta e seis centavos". */
export function moedaPorExtenso(valor: string): string {
  const limpo = valor.replace(/R\$\s?/, "").trim();
  const normalizado = limpo.includes(",") ? limpo.replace(/\./g, "").replace(",", ".") : limpo;
  const [inteiroTexto, centavosTexto = "0"] = normalizado.split(".");
  const reais = Number(inteiroTexto);
  const centavos = Number(centavosTexto.padEnd(2, "0").slice(0, 2));
  if (!Number.isFinite(reais) || !Number.isFinite(centavos)) return valor;

  const partes: string[] = [];
  if (reais) {
    // "um milhão de reais", mas "um milhão e duzentos mil reais"
    const redondoEmMilhoes = reais >= 1_000_000 && reais % 1_000_000 === 0;
    partes.push(`${inteiroPorExtenso(reais)}${redondoEmMilhoes ? " de" : ""} ${reais === 1 ? "real" : "reais"}`);
  }
  if (centavos) partes.push(`${inteiroPorExtenso(centavos)} ${centavos === 1 ? "centavo" : "centavos"}`);
  return partes.length ? partes.join(" e ") : "zero reais";
}
