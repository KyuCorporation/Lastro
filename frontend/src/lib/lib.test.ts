import { dividirEmTrechos } from "./destaques";
import { inteiroPorExtenso, moedaPorExtenso } from "./extenso";

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
