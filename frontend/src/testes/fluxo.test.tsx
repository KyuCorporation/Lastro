// Fluxo da tela central (T12): login → pergunta → resposta com números, citações e "Ver recibo".

import { act, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ErroApi } from "../api/http";
import { RESPOSTA_ANA, apiFalsa, montarApp, tokenEmMemoria } from "./montar";

async function entrarComo(email: string) {
  const usuario = userEvent.setup();
  await usuario.type(await screen.findByLabelText("E-mail"), email);
  await usuario.type(screen.getByLabelText("Senha"), "demo123");
  await usuario.click(screen.getByRole("button", { name: "Entrar" }));
  return usuario;
}

describe("login", () => {
  it("sem sessão, qualquer rota leva ao login", async () => {
    montarApp({ rota: "/recibos/x" });
    expect(await screen.findByRole("heading", { name: "Entrar no KYU" })).toBeInTheDocument();
  });

  it("senha errada mostra a mensagem da API e não entra", async () => {
    montarApp();
    const usuario = userEvent.setup();
    await usuario.type(await screen.findByLabelText("E-mail"), "ana@alfa.demo");
    await usuario.type(screen.getByLabelText("Senha"), "errada");
    await usuario.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("E-mail ou senha inválidos.");
    expect(screen.queryByText(/sessão expirou/)).not.toBeInTheDocument();
  });

  it("login válido guarda o token e mostra usuário, tenant e UFs", async () => {
    const { token } = montarApp();
    await entrarComo("ana@alfa.demo");
    expect(await screen.findByRole("heading", { name: "Consulta inteligente" })).toBeInTheDocument();
    expect(screen.getByText("Ana (analista)")).toBeInTheDocument();
    expect(screen.getByText("Analista de risco · Cliente Alfa")).toBeInTheDocument();
    expect(screen.getByLabelText("Estados autorizados: PE")).toBeInTheDocument();
    expect(token.ler()).toBe("token-ana@alfa.demo");
  });

  it("token guardado inválido volta ao login avisando que expirou", async () => {
    montarApp({ token: tokenEmMemoria("vencido") });
    expect(await screen.findByText("Sua sessão expirou. Entre novamente.")).toBeInTheDocument();
  });

  it("depois de sair, o próximo login começa na consulta, não na tela do usuário anterior", async () => {
    montarApp({ rota: "/acesso" });
    let usuario = await entrarComo("ana@alfa.demo");
    expect(await screen.findByRole("heading", { name: "Controle de acesso por perfil" })).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Sair" }));
    usuario = await entrarComo("gil@alfa.demo");
    expect(await screen.findByRole("heading", { name: "Consulta inteligente" })).toBeInTheDocument();
  });

  it("sair apaga o token", async () => {
    const { token } = montarApp();
    const usuario = await entrarComo("ana@alfa.demo");
    await usuario.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("heading", { name: "Entrar no KYU" })).toBeInTheDocument();
    expect(token.ler()).toBeNull();
  });
});

describe("consulta", () => {
  it("pergunta e recebe resposta com valores destacados, citações e recibo", async () => {
    const { api } = montarApp();
    const usuario = await entrarComo("ana@alfa.demo");
    await usuario.type(
      await screen.findByLabelText("Pergunta em linguagem natural"),
      "Quais contratos do CNPJ 99.999.999/0001-91 vencem nos próximos 6 meses?",
    );
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));

    const resultado = await screen.findByRole("region", { name: "Resposta com evidências" });
    expect(api.consultas.criar).toHaveBeenCalledWith({
      pergunta: "Quais contratos do CNPJ 99.999.999/0001-91 vencem nos próximos 6 meses?",
    });
    // valor destacado com leitura por extenso para leitor de tela
    expect(within(resultado).getByText("um milhão duzentos e cinquenta mil reais")).toHaveClass("sr-only");
    expect(within(resultado).getByText("14 de janeiro de 2027")).toBeInTheDocument();
    // citação [1] liga ao item da lista de fontes
    const link = within(resultado).getByRole("link", { name: "fonte 1" });
    const item = document.getElementById(link.getAttribute("href")!.slice(1));
    expect(item).toHaveTextContent("TCE-PE Dados Abertos");
    expect(within(item!).getByRole("link", { name: /Abrir na fonte oficial/ })).toHaveAttribute(
      "href",
      RESPOSTA_ANA.citacoes[0].url_origem,
    );
    expect(within(resultado).getByRole("link", { name: "Ver evidências" })).toHaveAttribute("href", "/recibos/recibo-1");
    expect(within(resultado).queryByRole("note")).not.toBeInTheDocument(); // dado real: sem selo sintético
  });

  it("negação aparece como acesso negado, em texto", async () => {
    const api = apiFalsa({
      consulta: async () => ({
        ...RESPOSTA_ANA,
        status: "negada",
        resposta: "Você não tem acesso a dados de AL.",
        citacoes: [],
        recibo_id: null,
      }),
    });
    montarApp({ api });
    const usuario = await entrarComo("ana@alfa.demo");
    await usuario.type(await screen.findByLabelText("Pergunta em linguagem natural"), "Quanto recebeu em Alagoas?");
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));
    const resultado = await screen.findByRole("region", { name: "Acesso negado" });
    expect(resultado).toHaveTextContent("Você não tem acesso a dados de AL.");
    expect(within(resultado).queryByRole("link", { name: "Ver evidências" })).not.toBeInTheDocument();
  });

  it("negação de escopo da API (403 ESCOPO_NEGADO) aparece no painel de acesso negado", async () => {
    const api = apiFalsa({
      consulta: async () => {
        throw new ErroApi(403, "ESCOPO_NEGADO", "Você não tem acesso a dados de AL.", "rid-403");
      },
    });
    montarApp({ api });
    const usuario = await entrarComo("ana@alfa.demo");
    await usuario.type(await screen.findByLabelText("Pergunta em linguagem natural"), "Quanto recebeu em Alagoas?");
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));
    const resultado = await screen.findByRole("region", { name: "Acesso negado" });
    expect(resultado).toHaveTextContent("Você não tem acesso a dados de AL.");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument(); // não é erro: é a regra funcionando
  });

  it("resposta sintética mostra o selo", async () => {
    montarApp({ api: apiFalsa({ consulta: async () => ({ ...RESPOSTA_ANA, sintetico: true }) }) });
    const usuario = await entrarComo("ana@alfa.demo");
    await usuario.type(await screen.findByLabelText("Pergunta em linguagem natural"), "x");
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));
    expect(await screen.findByRole("note")).toHaveTextContent("registro sintético");
  });

  it("erro da API (limite) aparece com a mensagem e o código do pedido", async () => {
    const api = apiFalsa({
      consulta: async () => {
        throw new ErroApi(429, "LIMITE_EXCEDIDO", "Limite de 30 consultas por minuto.", "rid-9");
      },
    });
    montarApp({ api });
    const usuario = await entrarComo("ana@alfa.demo");
    await usuario.type(await screen.findByLabelText("Pergunta em linguagem natural"), "x");
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));
    const alerta = await screen.findByRole("alert");
    expect(alerta).toHaveTextContent("Limite de 30 consultas por minuto.");
    expect(alerta).toHaveTextContent("rid-9");
  });

  it("gestor não vê o formulário de consulta", async () => {
    montarApp();
    await entrarComo("gil@alfa.demo");
    expect(await screen.findByRole("note")).toHaveTextContent("não faz consultas em linguagem natural");
    expect(screen.queryByLabelText("Pergunta em linguagem natural")).not.toBeInTheDocument();
  });

  it("sessão que cai no meio volta para o login", async () => {
    const api = apiFalsa();
    const { sessao } = montarApp({ api });
    await entrarComo("ana@alfa.demo");
    await screen.findByRole("heading", { name: "Consulta inteligente" });
    act(() => sessao.perder());
    await waitFor(() => expect(screen.getByRole("heading", { name: "Entrar no KYU" })).toBeInTheDocument());
    expect(screen.getByText("Sua sessão expirou. Entre novamente.")).toBeInTheDocument();
  });
});
