// T26: histórico de coletas na tela de fontes e a tela de métricas, com dados reais do banco e do eval.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { METRICAS, apiFalsa, montarApp, tokenEmMemoria } from "./montar";

async function montarLogado(email: string, rota = "/", api = apiFalsa()) {
  await api.auth.login({ email, senha: "demo123" });
  const r = montarApp({ api, rota, token: tokenEmMemoria(`token-${email}`) });
  await screen.findByRole("navigation", { name: "Principal" });
  return { ...r, usuario: userEvent.setup() };
}

describe("05 fontes: histórico de coletas", () => {
  it("lista as execuções com contagens, situação e o erro de quem falhou", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/fontes");
    const tabela = await screen.findByRole("table", { name: /Histórico de coletas/ });
    expect(api.fontes.execucoes).toHaveBeenCalled();
    const [ceis, pncp] = within(tabela).getAllByRole("row").slice(1);
    expect(ceis).toHaveTextContent("CEIS");
    expect(ceis).toHaveTextContent("14.700");
    expect(ceis).toHaveTextContent("14.604");
    expect(ceis).toHaveTextContent("96");
    expect(ceis).toHaveTextContent("Coletada");
    expect(pncp).toHaveTextContent("Falhou");
    expect(pncp).toHaveTextContent("FonteIndisponivel: 503 depois de 3 tentativas");
  });

  it("execução sem fim registrado aparece como sem conclusão, não como em andamento", async () => {
    const { EXECUCOES } = await import("./montar");
    const api = apiFalsa();
    api.fontes.execucoes = vi.fn(async () => [
      { ...EXECUCOES[0], id: "e9", status: "rodando", finalizada_em: null },
    ]);
    await montarLogado("ana@alfa.demo", "/fontes", api);
    const tabela = await screen.findByRole("table", { name: /Histórico de coletas/ });
    expect(tabela).toHaveTextContent("Sem conclusão");
    expect(tabela).not.toHaveTextContent("Em andamento");
  });
});

describe("08 métricas", () => {
  it("todo perfil vê Métricas no menu", async () => {
    await montarLogado("gil@alfa.demo");
    const menu = screen.getByRole("navigation", { name: "Principal" });
    expect(within(menu).getByRole("link", { name: "Métricas" })).toHaveAttribute("href", "/metricas");
  });

  it("mostra o gabarito e os ataques do eval, cada número com a meta", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/metricas");
    await screen.findByRole("heading", { name: "Métricas de qualidade" });
    expect(api.metricas.obter).toHaveBeenCalled();

    const gabarito = await screen.findByRole("region", { name: "Gabarito de perguntas" });
    expect(gabarito).toHaveTextContent("100 de 100 perguntas sem falha");
    const intent = within(gabarito).getByRole("group", { name: "Acerto de intent" });
    expect(intent).toHaveTextContent("100%");
    expect(intent).toHaveTextContent("meta ≥ 90%");
    expect(intent).toHaveTextContent("Meta atingida");
    expect(within(gabarito).getByRole("group", { name: "Citação correta" })).toHaveTextContent("42 respostas");
    expect(within(gabarito).getByRole("group", { name: "Resultado igual ao SQL de referência" })).toHaveTextContent(
      "1 pergunta com SQL de referência",
    );
    expect(gabarito).toHaveTextContent("modelo determinístico (sem LLM)");

    const ataques = screen.getByRole("region", { name: "Ataques de injeção e escopo" });
    expect(within(ataques).getByRole("group", { name: "Ataques bloqueados" })).toHaveTextContent("49 de 50");
    expect(within(ataques).getByRole("group", { name: "Ataques bloqueados" })).toHaveTextContent("Meta atingida");
    expect(within(ataques).getByRole("group", { name: "Vazamentos" })).toHaveTextContent("0");
    const categorias = within(ataques).getByRole("table", { name: /por categoria/ });
    expect(within(categorias).getAllByRole("row")).toHaveLength(3);
    expect(categorias).toHaveTextContent("Injeção direta na pergunta");

    expect(screen.getByRole("region", { name: "Cronômetro de diligência" })).toHaveTextContent("Ainda não medido");
  });

  it("meta não atingida aparece em texto", async () => {
    const api = apiFalsa({
      metricas: async () => ({
        ...METRICAS,
        eval: { ...METRICAS.eval, acerto_intent: 85 },
        ataques: { ...METRICAS.ataques, bloqueados: 40, pct_bloqueado: 80, vazamentos: 2 },
      }),
    });
    await montarLogado("ana@alfa.demo", "/metricas", api);
    const intent = await screen.findByRole("group", { name: "Acerto de intent" });
    expect(intent).toHaveTextContent("Abaixo da meta");
    expect(screen.getByRole("group", { name: "Vazamentos" })).toHaveTextContent("Abaixo da meta");
  });

  it("relatório ainda não gerado vira aviso com o comando, sem quebrar", async () => {
    const api = apiFalsa({ metricas: async () => ({ eval: null, ataques: null, cronometro: null, ultima_atualizacao: null }) });
    await montarLogado("ana@alfa.demo", "/metricas", api);
    const gabarito = await screen.findByRole("region", { name: "Gabarito de perguntas" });
    expect(gabarito).toHaveTextContent("Relatório ainda não gerado. Rode make eval.");
    expect(screen.getByRole("region", { name: "Ataques de injeção e escopo" })).toHaveTextContent("make eval-ataques");
  });

  it("cronômetro medido mostra as medidas, com os metadados só no subtítulo", async () => {
    const api = apiFalsa({
      metricas: async () => ({
        ...METRICAS,
        cronometro: {
          gerado_em: "2026-11-15T13:00:00+00:00",
          provedor_llm: "gemini",
          n_casos: 3,
          "mediana_sem_o_lastro_(min)": 38.5,
          "mediana_com_o_lastro_(min)": 4,
        },
      }),
    });
    await montarLogado("ana@alfa.demo", "/metricas", api);
    const cronometro = await screen.findByRole("region", { name: "Cronômetro de diligência" });
    expect(cronometro).toHaveTextContent("Mediana sem o lastro (min)38,5");
    expect(cronometro).toHaveTextContent("com 3 fornecedores");
    expect(cronometro).not.toHaveTextContent("N casos");
    expect(cronometro).not.toHaveTextContent("Provedor llm");
  });
});
