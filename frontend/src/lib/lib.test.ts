import { dividirEmTrechos } from "./destaques";
import { inteiroPorExtenso, moedaPorExtenso } from "./extenso";
import { cnpj, urlSegura } from "./formato";
import { valoresDaResposta } from "../features/recibo/leitura";
import { RECIBO_ANA } from "../testes/montar";
import { separarCnpjs } from "../features/carteiras/hooks";

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
  it("separa moeda, data, número e CNPJ", () => {
    const trechos = dividirEmTrechos("CNPJ 99.999.999/0001-91: 2 contratos, R$ 1.250.000,00, até 14/01/2027, 80%.");
    expect(trechos.filter((t) => t.tipo !== "texto")).toEqual([
      { tipo: "cnpj", texto: "99.999.999/0001-91" },
      { tipo: "numero", texto: "2" },
      { tipo: "moeda", texto: "R$ 1.250.000,00", falado: "um milhão duzentos e cinquenta mil reais" },
      { tipo: "data", texto: "14/01/2027", falado: "14 de janeiro de 2027" },
      { tipo: "numero", texto: "80%" },
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

describe("valores da resposta", () => {
  it("lista só o que é resultado, com o rótulo escrito pelo backend, na ordem dos marcadores", () => {
    expect(valoresDaResposta(RECIBO_ANA.conteudo)).toEqual([
      { marcador: "v3", rotulo: "Número de contratos que vencem no prazo", texto: "2" },
      { marcador: "v4", rotulo: "Valor somado dos contratos que vencem", texto: "R$ 1.250.000,00" },
      { marcador: "v5", rotulo: "Parte do valor vigente que vence no prazo", texto: "62,5%" },
    ]);
  });

  it("recibo antigo, sem significado, usa a descrição da origem", () => {
    const conteudo = {
      ...RECIBO_ANA.conteudo,
      valores: {
        v2: { valor: "300000", tipo: "moeda" as const, origem: "sum(pagamentos.valor)" },
        v9: { valor: "2027-01-14", tipo: "data" as const, origem: "min(vigencia_fim)" },
      },
    };
    expect(valoresDaResposta(conteudo)).toEqual([
      { marcador: "v2", rotulo: "Soma dos pagamentos", texto: "R$ 300.000,00" },
      { marcador: "v9", rotulo: "Min(vigencia_fim)", texto: "14/01/2027" },
    ]);
  });
});
