// Telas do N2 (T22): carteiras e fila, dossiê do fornecedor, selo do recibo e cadeia da auditoria.
// Passos 2 a 5 da demo pela interface, contra a API falsa (a real fica no E2E).

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ErroApi } from "../api/http";
import { apiFalsa, montarApp, tokenEmMemoria } from "./montar";

async function montarLogado(email: string, rota = "/", api = apiFalsa()) {
  await api.auth.login({ email, senha: "demo123" });
  const r = montarApp({ api, rota, token: tokenEmMemoria(`token-${email}`) });
  await screen.findByRole("navigation", { name: "Principal" });
  return { ...r, usuario: userEvent.setup() };
}

const PALAVRAS_PROIBIDAS = /fraude|irregular|suspeit|corrup/i;

describe("06 carteiras e fila", () => {
  it("lista as carteiras do cliente com link para a fila", async () => {
    await montarLogado("ana@alfa.demo", "/carteiras");
    await screen.findByRole("heading", { name: "Carteiras e fila" });
    const tabela = await screen.findByRole("table", { name: /carteiras do cliente/i });
    expect(within(tabela).getByText("Homologação")).toBeInTheDocument();
    expect(within(tabela).getByRole("link", { name: "Homologação 2026" })).toHaveAttribute("href", "/carteiras/cart-1");
  });

  it("analista cola CNPJs em qualquer formato, cria a carteira e vai para a fila", async () => {
    const api = apiFalsa({
      criarCarteira: async (e) => ({ id: "cart-1", nome: e.nome, finalidade: e.finalidade, n_itens: 2, cnpjs_invalidos: ["123"] }),
    });
    const { usuario } = await montarLogado("ana@alfa.demo", "/carteiras", api);
    await usuario.type(await screen.findByLabelText("Nome da carteira"), "Renovação de limpeza");
    await usuario.selectOptions(screen.getByLabelText("Finalidade"), "renovacao");
    await usuario.type(
      screen.getByLabelText(/CNPJs/),
      "99.999.999/0001-91, 11222333000181{enter}123",
    );
    await usuario.click(screen.getByRole("button", { name: "Criar carteira" }));

    expect(api.carteiras.criar).toHaveBeenCalledWith({
      nome: "Renovação de limpeza",
      finalidade: "renovacao",
      cnpjs: ["99.999.999/0001-91", "11222333000181", "123"],
    });
    await screen.findByRole("heading", { name: "Fila da carteira" });
    expect(screen.getByRole("status")).toHaveTextContent("1 CNPJ ignorado por ser inválido: 123");
  });

  it("gestor vê as carteiras, mas não o formulário de criação", async () => {
    const { api } = await montarLogado("gil@alfa.demo", "/carteiras");
    await screen.findByRole("table", { name: /carteiras do cliente/i });
    expect(screen.queryByRole("button", { name: "Criar carteira" })).not.toBeInTheDocument();
    expect(api.carteiras.criar).not.toHaveBeenCalled();
  });

  it("fila mostra prioridade, sinais em texto, explicação, evidência, regra e link para o dossiê", async () => {
    await montarLogado("ana@alfa.demo", "/carteiras/cart-1");
    await screen.findByRole("heading", { name: "Fila da carteira" });
    const itens = await screen.findAllByRole("listitem", { name: /fornecedor/i });
    expect(itens).toHaveLength(2);

    const primeiro = itens[0];
    expect(primeiro).toHaveTextContent("FORNECEDOR ALFA LTDA");
    expect(primeiro).toHaveTextContent("99.999.999/0001-91");
    expect(primeiro).toHaveTextContent("Prioridade 61,5");
    expect(primeiro).toHaveTextContent("R$ 1.250.000,00");
    expect(primeiro).toHaveTextContent("Forte · Sanção vigente");
    expect(primeiro).toHaveTextContent("Atenção · Vencimentos concentrados");
    expect(primeiro).toHaveTextContent("62% do valor vigente termina em até 180 dias.");
    expect(within(primeiro).getByRole("link", { name: /Sanção 1/ })).toHaveAttribute(
      "href",
      "https://portaldatransparencia.gov.br/sancoes/ceis/1",
    );
    expect(within(primeiro).getByRole("link", { name: /Abrir dossiê/ })).toHaveAttribute(
      "href",
      "/fornecedores/99999999000191",
    );

    expect(itens[1]).toHaveTextContent("Nenhum sinal para investigar");
    expect(screen.getByText(/peso da gravidade × log10\(1 \+ valor exposto\)/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(PALAVRAS_PROIBIDAS);
  });

  it("carteira de outro cliente (404) mostra o erro, sem itens", async () => {
    await montarLogado("ana@alfa.demo", "/carteiras/outra");
    expect(await screen.findByRole("alert")).toHaveTextContent("Carteira não encontrada.");
    expect(screen.queryAllByRole("listitem", { name: /fornecedor/i })).toHaveLength(0);
  });

  it("o menu marca Carteiras na fila e no dossiê", async () => {
    await montarLogado("ana@alfa.demo", "/fornecedores/99999999000191");
    const menu = screen.getByRole("navigation", { name: "Principal" });
    expect(within(menu).getByRole("link", { name: "Carteiras" })).toHaveAttribute("aria-current", "page");
  });
});

describe("07 dossiê do fornecedor", () => {
  it("reúne resumo, contratos, sanções, sinais, sócios e fontes, cada item com a origem", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/fornecedores/99999999000191");
    await screen.findByRole("heading", { name: "Dossiê do fornecedor" });
    expect(api.fornecedores.dossie).toHaveBeenCalledWith("99999999000191");
    expect(await screen.findByText("FORNECEDOR ALFA LTDA")).toBeInTheDocument();
    expect(screen.getByText(/99\.999\.999\/0001-91/)).toBeInTheDocument();

    const resumo = screen.getByRole("region", { name: "Resumo por estado" });
    expect(resumo).toHaveTextContent("Pernambuco");
    expect(resumo).toHaveTextContent("R$ 1.800.000,00");

    const vigentes = screen.getByRole("region", { name: "Contratos vigentes" });
    expect(vigentes).toHaveTextContent("Limpeza hospitalar");
    expect(vigentes).toHaveTextContent("14/01/2027");
    expect(within(vigentes).getByRole("link", { name: /ctr:2025:001/ })).toHaveAttribute(
      "href",
      "https://sistemas.tcepe.tc.br/DadosAbertos/Contratos!json?AnoReferencia=2025",
    );

    expect(screen.getByRole("region", { name: "Vencendo em 180 dias" })).toHaveTextContent("Nenhum contrato");
    const sancoes = screen.getByRole("region", { name: "Sanções" });
    expect(sancoes).toHaveTextContent("Impedimento");
    expect(sancoes).toHaveTextContent("Vigente");
    const sinais = screen.getByRole("region", { name: "Sinais para investigar" });
    expect(sinais).toHaveTextContent("Forte · Sanção vigente");
    expect(sinais).toHaveTextContent("regra v1");
    expect(screen.getByRole("region", { name: "Sócios" })).toHaveTextContent("***.456.789-** JOSÉ");
    const fontes = screen.getByRole("region", { name: "Fontes consultadas" });
    expect(fontes).toHaveTextContent("TCE-PE Dados Abertos");
    expect(fontes).toHaveTextContent("CEIS");
    expect(document.body.textContent).not.toMatch(PALAVRAS_PROIBIDAS);
  });

  it("perfil sem acesso a sócios vê o aviso, não a lista", async () => {
    const { DOSSIE } = await import("./montar");
    const api = apiFalsa({ dossie: async () => ({ ...DOSSIE, socios: null }) });
    await montarLogado("gil@alfa.demo", "/fornecedores/99999999000191", api);
    const socios = await screen.findByRole("region", { name: "Sócios" });
    expect(socios).toHaveTextContent("Seu perfil não acessa o quadro societário.");
  });

  it("CNPJ inválido mostra o erro da API", async () => {
    const api = apiFalsa({
      dossie: async () => {
        throw new ErroApi(422, "ENTRADA_INVALIDA", "CNPJ inválido.", "rid-422");
      },
    });
    await montarLogado("ana@alfa.demo", "/fornecedores/123", api);
    expect(await screen.findByRole("alert")).toHaveTextContent("CNPJ inválido.");
  });
});

describe("02 recibo: selo de integridade", () => {
  it("mostra 'íntegro' quando o hash recalculado confere", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/recibos/recibo-1");
    const selo = await screen.findByRole("status", { name: "Integridade do recibo" });
    await waitFor(() => expect(selo).toHaveTextContent("Íntegro"));
    expect(api.recibos.verificar).toHaveBeenCalledWith("recibo-1");
  });

  it("mostra 'alterado' quando o hash não confere", async () => {
    const api = apiFalsa({
      verificarRecibo: async () => ({ integro: false, hash_gravado: "a".repeat(64), hash_recalculado: "f".repeat(64) }),
    });
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1", api);
    const selo = await screen.findByRole("status", { name: "Integridade do recibo" });
    await waitFor(() => expect(selo).toHaveTextContent("Alterado depois de gravado"));
  });
});

describe("04 auditoria: cadeia de eventos", () => {
  it("auditor vê o selo da cadeia e os eventos encadeados", async () => {
    const { api } = await montarLogado("caio@alfa.demo", "/auditoria");
    const cadeia = await screen.findByRole("region", { name: "Cadeia de auditoria" });
    await waitFor(() => expect(cadeia).toHaveTextContent("Cadeia íntegra · 12 eventos conferidos"));
    expect(api.auditoria.listar).toHaveBeenCalled();
    const eventos = within(cadeia).getByRole("table", { name: /eventos da cadeia/i });
    expect(eventos).toHaveTextContent("Consulta");
    expect(eventos).toHaveTextContent("Acesso negado");
    expect(eventos).toHaveTextContent("uf_fora_do_escopo");
  });

  it("cadeia quebrada aponta o primeiro evento alterado", async () => {
    const api = apiFalsa({ cadeia: async () => ({ integra: false, n_eventos: 12, primeiro_seq_quebrado: 7 }) });
    await montarLogado("caio@alfa.demo", "/auditoria", api);
    const cadeia = await screen.findByRole("region", { name: "Cadeia de auditoria" });
    await waitFor(() => expect(cadeia).toHaveTextContent("Cadeia alterada a partir do evento 7"));
  });

  it("analista não chama a auditoria do cliente (a API responderia 403)", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/auditoria");
    await screen.findByRole("heading", { name: "Auditoria de consultas" });
    expect(screen.queryByRole("region", { name: "Cadeia de auditoria" })).not.toBeInTheDocument();
    expect(api.auditoria.verificar).not.toHaveBeenCalled();
  });
});
