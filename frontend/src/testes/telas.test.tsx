// As 5 telas do design ligadas à API (falsa aqui; real no E2E): moldura, consulta, recibo, acesso,
// auditoria e fontes.

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ErroApi } from "../api/http";
import { PEDIDO_DE_ATAQUE } from "../features/consulta/TesteSeguranca";
import { HISTORICO, RECIBO_ANA, RESPOSTA_ANA, apiFalsa, montarApp, tokenEmMemoria } from "./montar";

// O AuthProvider valida o token guardado com GET /me: o backend falso precisa de um login antes.
async function montarLogado(email: string, rota = "/", api = apiFalsa()) {
  await api.auth.login({ email, senha: "demo123" });
  const r = montarApp({ api, rota, token: tokenEmMemoria(`token-${email}`) });
  await screen.findByRole("navigation", { name: "Principal" });
  return { ...r, usuario: userEvent.setup() };
}

describe("moldura", () => {
  it("mostra a marca, o menu e o escopo da sessão no topo", async () => {
    await montarLogado("ana@alfa.demo");
    const menu = screen.getByRole("navigation", { name: "Principal" });
    expect(within(menu).getAllByRole("link").map((l) => l.textContent)).toEqual([
      "Consulta",
      "Fontes e catálogo",
      "Acesso",
      "Auditoria",
    ]);
    expect(within(menu).getByRole("link", { name: "Consulta" })).toHaveAttribute("aria-current", "page");
    expect(screen.getByText("KYU")).toBeInTheDocument();
    expect(screen.getByText("Portal de transparência")).toBeInTheDocument();
    expect(screen.getByLabelText("Estados autorizados: PE")).toHaveTextContent("Pernambuco");
  });

  it("gestor não vê Auditoria no menu (GET /consultas responderia 403)", async () => {
    await montarLogado("gil@alfa.demo");
    const menu = screen.getByRole("navigation", { name: "Principal" });
    expect(within(menu).queryByRole("link", { name: "Auditoria" })).not.toBeInTheDocument();
  });

  it("o recibo mantém Consulta marcada no menu", async () => {
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1");
    await screen.findByRole("heading", { name: "Recibo de evidências" });
    const menu = screen.getByRole("navigation", { name: "Principal" });
    expect(within(menu).getByRole("link", { name: "Consulta" })).toHaveAttribute("aria-current", "page");
  });
});

describe("01 consulta inteligente", () => {
  it("resposta traz valor, resumo e integridade lidos do recibo", async () => {
    const { usuario, api } = await montarLogado("ana@alfa.demo");
    await usuario.type(screen.getByLabelText("Pergunta em linguagem natural"), RECIBO_ANA.conteudo.pergunta);
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));

    const resposta = await screen.findByRole("region", { name: "Resposta com evidências" });
    expect(await within(resposta).findByText("Valor total registrado: R$ 1.250.000,00")).toBeInTheDocument();
    expect(api.recibos.obter).toHaveBeenCalledWith("recibo-1");
    expect(resposta).toHaveTextContent("2 registros de contrato encontrados");
    expect(resposta).toHaveTextContent("Período considerado: próximos 180 dias a partir de 06/11/2026");
    expect(resposta).toHaveTextContent("Nenhuma informação de sanção foi consultada nesta busca");
    expect(within(resposta).getByRole("link", { name: "Ver evidências" })).toHaveAttribute("href", "/recibos/recibo-1");

    const integridade = screen.getByRole("region", { name: "Integridade da consulta" });
    expect(integridade).toHaveTextContent("Escopo: PE");
    expect(integridade).toHaveTextContent("TCE-PE Dados Abertos");
    expect(integridade).toHaveTextContent("Perfil validado antes da busca");
    expect(integridade).toHaveTextContent("Texto conferido pelo verificador");
  });

  it("teste de segurança manda o ataque para a API e mostra o bloqueio real", async () => {
    const api = apiFalsa({
      consulta: async () => {
        throw new ErroApi(403, "ESCOPO_NEGADO", "Pedido fora das regras do sistema.", "rid-ataque");
      },
    });
    const { usuario } = await montarLogado("ana@alfa.demo", "/", api);
    const cartao = screen.getByRole("region", { name: "Teste de segurança" });
    expect(cartao).toHaveTextContent(`Tentativa: "${PEDIDO_DE_ATAQUE}"`);
    await usuario.click(within(cartao).getByRole("button", { name: "Executar teste" }));
    expect(await within(cartao).findByText("Bloqueada: Pedido fora das regras do sistema.")).toBeInTheDocument();
    expect(api.consultas.criar).toHaveBeenCalledWith({ pergunta: PEDIDO_DE_ATAQUE });
  });

  it("teste de segurança diz quando o backend NÃO bloqueou (nada é encenado)", async () => {
    const { usuario } = await montarLogado(
      "ana@alfa.demo",
      "/",
      apiFalsa({ consulta: async () => RESPOSTA_ANA }),
    );
    const cartao = screen.getByRole("region", { name: "Teste de segurança" });
    await usuario.click(within(cartao).getByRole("button", { name: "Executar teste" }));
    expect(await within(cartao).findByText(/^Não bloqueada:/)).toBeInTheDocument();
  });

  it("gestor não vê o teste de segurança", async () => {
    await montarLogado("gil@alfa.demo");
    expect(screen.queryByRole("region", { name: "Teste de segurança" })).not.toBeInTheDocument();
  });
});

describe("02 recibo de evidências", () => {
  it("mostra valor, registros com link de origem, total reproduzível e selo", async () => {
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1");
    await screen.findByRole("heading", { name: "Recibo de evidências" });
    expect(screen.getByText("R$ 1.250.000,00")).toBeInTheDocument();
    expect(screen.getByText("2 registros relacionados")).toBeInTheDocument();

    const tabela = screen.getByRole("table");
    const linhas = within(tabela).getAllByRole("row").slice(1);
    expect(linhas).toHaveLength(2);
    expect(linhas[0]).toHaveTextContent("ctr:2025:001");
    expect(within(linhas[0]).getByRole("link", { name: /Registro 01/ })).toHaveAttribute(
      "href",
      RECIBO_ANA.conteudo.linhas[0].url_origem,
    );
    expect(linhas[1]).toHaveTextContent("Registro 02 · sem link público");

    expect(screen.getByText("Total reproduzível: soma do valor global dos contratos = R$ 1.250.000,00")).toBeInTheDocument();
    expect(screen.getByText(RECIBO_ANA.hash)).toBeInTheDocument();
    expect(screen.getByText("aprovado pelo verificador")).toBeInTheDocument();
  });

  it("recibo de outro usuário (404) mostra o erro, sem dados", async () => {
    await montarLogado("ana@alfa.demo", "/recibos/de-outro");
    expect(await screen.findByRole("alert")).toHaveTextContent("Recibo não encontrado.");
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
  });
});

describe("03 controle de acesso", () => {
  it("mostra a sessão, a negação fora do escopo e a matriz com o perfil atual", async () => {
    await montarLogado("ana@alfa.demo", "/acesso");
    expect(await screen.findByRole("heading", { name: "Controle de acesso por perfil" })).toBeInTheDocument();
    const sessao = screen.getByRole("region", { name: "Sessão atual" });
    expect(sessao).toHaveTextContent("Acesso ativo");
    expect(sessao).toHaveTextContent("Estado autorizado: Pernambuco (PE)");
    expect(screen.getByRole("region", { name: "Tentativa fora do escopo" })).toHaveTextContent("Acesso negado");
    const linha = screen.getByRole("rowheader", { name: /Analista de risco/ });
    expect(linha).toHaveTextContent("(você)");
    expect(screen.getAllByRole("rowheader")).toHaveLength(4);
  });
});

describe("04 auditoria de consultas", () => {
  it("lista o histórico da API e filtra por resultado", async () => {
    const { usuario, api } = await montarLogado("ana@alfa.demo", "/auditoria");
    const tabela = await screen.findByRole("table");
    expect(api.consultas.listar).toHaveBeenCalledWith(50);
    expect(within(tabela).getAllByRole("row")).toHaveLength(1 + HISTORICO.length);
    expect(within(tabela).getByRole("link", { name: "Ver recibo" })).toHaveAttribute("href", "/recibos/recibo-1");
    expect(tabela).toHaveTextContent("Permissão negada");
    expect(tabela).toHaveTextContent("Outro usuário do cliente");

    await usuario.click(screen.getByRole("button", { name: "Bloqueadas" }));
    await waitFor(() => expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(2));
    expect(screen.getByRole("table")).toHaveTextContent("Bloqueada");
    expect(screen.getByRole("button", { name: "Bloqueadas" })).toHaveAttribute("aria-pressed", "true");

    await usuario.click(screen.getByRole("button", { name: "Sem dados" }));
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(2);
    expect(screen.getByRole("table")).toHaveTextContent("Sem evidência");
  });

  it("auditor vê as consultas do cliente", async () => {
    await montarLogado("caio@alfa.demo", "/auditoria");
    expect(await screen.findByText(/Consultas de todo o cliente/)).toBeInTheDocument();
  });

  it("gestor não chama a API (evita 403 e negação na auditoria)", async () => {
    const { api } = await montarLogado("gil@alfa.demo", "/auditoria");
    expect(await screen.findByRole("note")).toHaveTextContent("não acompanha o histórico");
    expect(api.consultas.listar).not.toHaveBeenCalled();
  });
});

describe("05 fonte e catálogo", () => {
  it("mostra a fonte, o catálogo a confirmar e o pipeline, sem contagens", async () => {
    await montarLogado("ana@alfa.demo", "/fontes");
    expect(await screen.findByRole("heading", { name: "Fonte e catálogo de dados" })).toBeInTheDocument();
    expect(screen.getByText("Tribunal de Contas do Estado de Pernambuco (TCE-PE)")).toBeInTheDocument();
    expect(screen.getByText("A validar · API / endpoint")).toBeInTheDocument();
    expect(screen.getAllByText("A confirmar")).toHaveLength(3);
    expect(screen.getByRole("region", { name: "Pipeline de dados" })).toHaveTextContent("Catálogo KYU");
    expect(screen.getByText("Não exibir contagens ou status como reais até a primeira sincronização bem-sucedida.")).toBeInTheDocument();
  });
});
