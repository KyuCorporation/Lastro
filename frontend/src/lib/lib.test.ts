import { dividirEmTrechos } from "./destaques";
import { inteiroPorExtenso, moedaPorExtenso } from "./extenso";
import { cnpj, urlSegura } from "./formato";
import { separarCnpjs } from "../features/carteiras/hooks";
import { POR_UF, SANCOES, sugestoesPara } from "../features/consulta/perguntasSugeridas";

describe("extenso", () => {
  it.each([
    [0, "zero"],
    [1, "um"],
    [16, "dezesseis"],
    [21, "vinte e um"],
    [100, "cem"],
    [101, "cento e um"],
    [999, "novecentos e noventa e nove"],
    [1000, "mil"],
    [1500, "mil e quinhentos"],
    [2010, "dois mil e dez"],
    [1234, "mil duzentos e trinta e quatro"],
    [1_000_000, "um milhão"],
    [2_500_000, "dois milhões quinhentos mil"],
  ])("%i → %s", (n, esperado) => {
    expect(inteiroPorExtenso(n)).toBe(esperado);
  });

  it.each([
    ["R$ 1.250.000,00", "um milhão duzentos e cinquenta mil reais"],
    ["R$ 1,00", "um real"],
    ["1234.56", "mil duzentos e trinta e quatro reais e cinquenta e seis centavos"],
    ["R$ 0,01", "um centavo"],
    ["R$ 3.000.000,00", "três milhões de reais"],
  ])("%s → %s", (valor, esperado) => {
    expect(moedaPorExtenso(valor)).toBe(esperado);
  });
});

describe("destaques", () => {
  it("separa moeda, data, número, CNPJ e citação", () => {
    const trechos = dividirEmTrechos(
      "CNPJ 99.999.999/0001-91: 2 contratos, R$ 1.250.000,00 [1], até 14/01/2027, 80% [2].",
    );
    expect(trechos.filter((t) => t.tipo !== "texto")).toEqual([
      { tipo: "cnpj", texto: "99.999.999/0001-91" },
      { tipo: "numero", texto: "2" },
      { tipo: "moeda", texto: "R$ 1.250.000,00", falado: "um milhão duzentos e cinquenta mil reais" },
      { tipo: "citacao", texto: "[1]", n: 1 },
      { tipo: "data", texto: "14/01/2027", falado: "14 de janeiro de 2027" },
      { tipo: "numero", texto: "80%" },
      { tipo: "citacao", texto: "[2]", n: 2 },
    ]);
  });

  it("mantém o texto inteiro ao juntar os trechos", () => {
    const texto = "Sem números aqui, só texto.";
    expect(dividirEmTrechos(texto)).toEqual([{ tipo: "texto", texto }]);
  });
});

describe("formatos do N2", () => {
  it("formata CNPJ com 14 dígitos e devolve o resto como veio", () => {
    expect(cnpj("99999999000191")).toBe("99.999.999/0001-91");
    expect(cnpj("123")).toBe("123");
  });

  it("só aceita link http(s) vindo de fonte externa", () => {
    expect(urlSegura("https://pncp.gov.br/x")).toBe("https://pncp.gov.br/x");
    expect(urlSegura("javascript:alert(1)")).toBeNull();
    expect(urlSegura("about:blank#teste")).toBeNull();
    expect(urlSegura(null)).toBeNull();
  });

  it("separa CNPJs colados por linha, vírgula, ponto e vírgula ou espaço", () => {
    expect(separarCnpjs(" 99.999.999/0001-91,11222333000181\n\n123 ; 456 ")).toEqual([
      "99.999.999/0001-91",
      "11222333000181",
      "123",
      "456",
    ]);
  });
});

function cnpjValido(texto: string): boolean {
  const d = texto.replace(/\D/g, "");
  if (d.length !== 14 || /^(\d)+$/.test(d)) return false;
  const digito = (base: string) => {
    const pesos = base.length === 12 ? [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] : [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2];
    const resto = [...base].reduce((soma, n, i) => soma + Number(n) * pesos[i], 0) % 11;
    return resto < 2 ? "0" : String(11 - resto);
  };
  const d1 = digito(d.slice(0, 12));
  return d.slice(12) === d1 + digito(d.slice(0, 12) + d1);
}

describe("perguntas sugeridas", () => {
  it("Pernambuco tem sugestões próprias, antes das de sanção", () => {
    const pe = sugestoesPara(["PE"]);
    expect(pe.slice(0, POR_UF.PE.length)).toEqual(POR_UF.PE);
    expect(POR_UF.PE.length).toBeGreaterThanOrEqual(4);
    expect(pe.some((s) => /Alagoas|AL/.test(s))).toBe(false);
  });

  it("todo CNPJ citado tem dígito verificador válido", () => {
    const perguntas = [...Object.values(POR_UF).flat(), ...SANCOES];
    const cnpjs = perguntas.flatMap((p) => p.match(/\d{2}\.\d{3}\.\d{3}\/\d{4}-\d{2}/g) ?? []);
    expect(cnpjs.length).toBeGreaterThan(0);
    expect(cnpjs.filter((c) => !cnpjValido(c))).toEqual([]);
  });
});
