// Telas do N2 (T22): carteiras e fila, dossiê do fornecedor, selo do recibo e cadeia da auditoria.
// Passos 2 a 5 da demo pela interface, contra a API falsa (a real fica no E2E).

import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ErroApi } from "../api/http";
import type { Alerta } from "../api/types";
import { DOSSIE, RECIBO_ANA, apiFalsa, montarApp, tokenEmMemoria } from "./montar";

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

  it("alertas abertos: sinal, carteira e data; UF fora do escopo e sinal que deixou de valer", async () => {
    const api = apiFalsa({
      alertas: async () => [
        {
          id: "al-1",
          carteira_id: "cart-1",
          cnpj: "99999999000191",
          sinal: { id: "s-1", tipo: "sancao_direta", gravidade: "forte", uf: null, explicacao: "Consta 1 sanção vigente no CEIS." },
          status: "aberto",
          criado_em: "2026-11-17T12:00:00Z",
        },
        {
          id: "al-2",
          carteira_id: "cart-1",
          cnpj: "99999999000191",
          sinal: { id: null, tipo: "penhasco", gravidade: "atencao", uf: "PE", explicacao: "75,0% do valor vigente em PE termina em até 180 dias." },
          status: "aberto",
          criado_em: "2026-11-16T12:00:00Z",
        },
        { id: "al-3", carteira_id: "cart-1", cnpj: "11222333000181", sinal: null, status: "aberto", criado_em: "2026-11-16T12:00:00Z" },
      ],
    });
    await montarLogado("ana@alfa.demo", "/carteiras", api);
    const tabela = await screen.findByRole("table", { name: "Alertas abertos do cliente" });
    expect(api.alertas.listar).toHaveBeenCalledWith("aberto");
    expect(screen.getByText(/3 sinais para investigar/)).toBeInTheDocument();
    const linhas = within(tabela).getAllByRole("row").slice(1);
    expect(within(linhas[0]).getByRole("link", { name: "99.999.999/0001-91" })).toHaveAttribute("href", "/fornecedores/99999999000191");
    expect(linhas[0]).toHaveTextContent("Sanção vigente");
    expect(linhas[0]).toHaveTextContent("Forte");
    expect(within(linhas[0]).getByRole("link", { name: "Homologação 2026" })).toHaveAttribute("href", "/carteiras/cart-1");
    expect(linhas[1]).toHaveTextContent("Deixou de valer no último cálculo dos sinais.");
    expect(linhas[2]).toHaveTextContent("Sinal de UF fora do seu escopo");
    expect(tabela.textContent).not.toMatch(PALAVRAS_PROIBIDAS);
  });

  it("analista marca o alerta como visto ou resolve, e ele sai da lista", async () => {
    let abertos: Alerta[] = [
      {
        id: "al-1",
        carteira_id: "cart-1",
        cnpj: "99999999000191",
        sinal: { id: "s-1", tipo: "sancao_direta", gravidade: "forte", uf: null, explicacao: "Consta 1 sanção vigente no CEIS." },
        status: "aberto",
        criado_em: "2026-11-17T12:00:00Z",
      },
    ];
    const api = apiFalsa({
      alertas: async () => abertos,
      atualizarAlerta: async (id, status) => {
        abertos = abertos.filter((a) => a.id !== id);
        return { id, status };
      },
    });
    const { usuario } = await montarLogado("ana@alfa.demo", "/carteiras", api);
    expect(await screen.findByRole("button", { name: "Resolver: 99.999.999/0001-91, Sanção vigente" })).toBeInTheDocument();
    await usuario.click(screen.getByRole("button", { name: "Marcar como visto: 99.999.999/0001-91, Sanção vigente" }));
    expect(api.alertas.atualizar).toHaveBeenCalledWith("al-1", "visto");
    await waitFor(() => expect(screen.queryByRole("heading", { name: "Alertas abertos" })).not.toBeInTheDocument());
  });

  it("gestor vê os alertas abertos sem os botões de mudar o status", async () => {
    const alerta: Alerta = {
      id: "al-1",
      carteira_id: "cart-1",
      cnpj: "99999999000191",
      sinal: { id: "s-1", tipo: "sancao_direta", gravidade: "forte", uf: null, explicacao: "Consta 1 sanção vigente no CEIS." },
      status: "aberto",
      criado_em: "2026-11-17T12:00:00Z",
    };
    await montarLogado("gil@alfa.demo", "/carteiras", apiFalsa({ alertas: async () => [alerta] }));
    await screen.findByRole("table", { name: "Alertas abertos do cliente" });
    expect(screen.queryByRole("button", { name: /Marcar como visto|Resolver/ })).not.toBeInTheDocument();
  });

  it("sem alerta aberto, a seção não aparece", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/carteiras");
    await screen.findByRole("table", { name: /carteiras do cliente/i });
    await waitFor(() => expect(api.alertas.listar).toHaveBeenCalled());
    expect(screen.queryByRole("heading", { name: "Alertas abertos" })).not.toBeInTheDocument();
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
    expect(primeiro).toHaveTextContent("regra v2 · calculado em 17/11/2026");
    expect(within(primeiro).getByRole("link", { name: /Sanção 1/ })).toHaveAttribute(
      "href",
      "https://portaldatransparencia.gov.br/sancoes/ceis/1",
    );
    expect(within(primeiro).getByRole("link", { name: /Abrir dossiê/ })).toHaveAttribute(
      "href",
      "/fornecedores/99999999000191",
    );

    // CNPJ sem nenhum dado visível: diz isso em texto e não oferece um dossiê que daria "não encontrado".
    expect(itens[1]).toHaveTextContent("Sem registros nas fontes autorizadas para você");
    expect(within(itens[1]).queryByRole("link", { name: /Abrir dossiê/ })).not.toBeInTheDocument();
    expect(screen.getByText(/Os sinais vêm do último cálculo da base/)).toBeInTheDocument();
    expect(screen.getByText(/peso da gravidade × log10\(1 \+ valor exposto\)/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(PALAVRAS_PROIBIDAS);
  });

  it("sinal com muitas evidências mostra três e recolhe o resto", async () => {
    const { FILA } = await import("./montar");
    const evidencias = Array.from({ length: 10 }, (_, i) => ({
      tabela: "contratos", id: `ct-${i}`, url_origem: `https://exemplo.gov.br/contrato/${i}`,
    }));
    const item = { ...FILA.itens[0], sinais: [{ ...FILA.itens[0].sinais[1], evidencias }] };
    const api = apiFalsa({ fila: async () => ({ ...FILA, itens: [item] }) });
    await montarLogado("ana@alfa.demo", "/carteiras/cart-1", api);
    const [primeiro] = await screen.findAllByRole("listitem", { name: /fornecedor/i });
    expect(within(primeiro).getByText("e mais 7 registros")).toBeInTheDocument();
    expect(within(primeiro).getAllByRole("link", { name: /Contrato \d+/ })).toHaveLength(3);
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
  it("sanção retirada do cadastro da CGU aparece com a data, não como vigente", async () => {
    const [s] = DOSSIE.sancoes;
    const api = apiFalsa({
      dossie: async () => ({ ...DOSSIE, sancoes: [{ ...s!, vigente: false, removida_em: "2026-11-10T12:00:00Z" }] }),
    });
    await montarLogado("ana@alfa.demo", "/fornecedores/99999999000191", api);
    const sancoes = await screen.findByRole("region", { name: "Sanções" });
    expect(sancoes).toHaveTextContent("Retirada do cadastro em 10/11/2026");
    expect(sancoes).not.toHaveTextContent("Vigente");
  });

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
    const cobertura = screen.getByRole("region", { name: "Cobertura deste dossiê" });
    expect(cobertura).toHaveTextContent("TCE-PE Dados Abertos");
    expect(cobertura).toHaveTextContent("CEIS");
    expect(cobertura).toHaveTextContent("Sinais calculados em 06/11/2026");
    expect(cobertura).toHaveTextContent("Ausência de sinal não é atestado de regularidade");
    // Liquidação não é pagamento: a tabela usa o nome certo e explica.
    expect(within(resumo).getAllByRole("columnheader").map((c) => c.textContent)).toEqual([
      "Estado", "Contratos", "Valor contratado", "Valor vigente", "Liquidações", "Valor liquidado", "Valor empenhado",
    ]);
    expect(resumo).toHaveTextContent("Liquidado: despesa reconhecida pelo órgão");
    expect(document.body.textContent).not.toMatch(PALAVRAS_PROIBIDAS);
  });

  it("perfil sem acesso a sócios vê o aviso, não a lista", async () => {
    const { DOSSIE } = await import("./montar");
    const api = apiFalsa({ dossie: async () => ({ ...DOSSIE, socios: null }) });
    await montarLogado("gil@alfa.demo", "/fornecedores/99999999000191", api);
    const socios = await screen.findByRole("region", { name: "Sócios" });
    expect(socios).toHaveTextContent("Seu perfil não acessa o quadro societário.");
  });

  it("sem sinais, o selo é neutro e não parece atestado", async () => {
    const { DOSSIE } = await import("./montar");
    const api = apiFalsa({ dossie: async () => ({ ...DOSSIE, sinais: [] }) });
    await montarLogado("ana@alfa.demo", "/fornecedores/99999999000191", api);
    const selo = await screen.findByText("Nenhum sinal nas fontes consultadas");
    expect(selo.className).not.toMatch(/verde/);
    const cobertura = screen.getByRole("region", { name: "Cobertura deste dossiê" });
    expect(cobertura).toHaveTextContent("Ausência de sinal não é atestado de regularidade");
    expect(cobertura).not.toHaveTextContent("Sinais calculados em");
  });

  it("fornecedor sem registros (404) vira aviso neutro, não erro", async () => {
    const api = apiFalsa({
      dossie: async () => {
        throw new ErroApi(404, "NAO_ENCONTRADO", "Não há registros deste fornecedor nas fontes autorizadas para você.", "rid-404");
      },
    });
    await montarLogado("ana@alfa.demo", "/fornecedores/11222333000181", api);
    const aviso = await screen.findByRole("region", { name: "Sem registros deste fornecedor" });
    expect(aviso).toHaveTextContent("11.222.333/0001-81");
    expect(aviso).toHaveTextContent("nas fontes autorizadas para você");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
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

  it("auditor vê a cabeça da cadeia inteira para publicar fora do Lastro e pode copiar o hash", async () => {
    const { usuario, api } = await montarLogado("caio@alfa.demo", "/auditoria");
    const copiar = vi.spyOn(navigator.clipboard, "writeText"); // o userEvent instala uma área de transferência falsa
    const cabeca = await screen.findByRole("region", { name: "Cabeça da cadeia" });
    expect(api.auditoria.cabeca).toHaveBeenCalled();
    await waitFor(() => expect(cabeca).toHaveTextContent("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff"));
    expect(cabeca).toHaveTextContent("Evento nº 42");
    expect(cabeca).toHaveTextContent("12 eventos");
    await usuario.click(within(cabeca).getByRole("button", { name: "Copiar o hash da cabeça" }));
    expect(copiar).toHaveBeenCalledWith("ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff");
    expect(await within(cabeca).findByRole("status")).toHaveTextContent("Hash copiado");
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

describe("contexto por carteira na consulta (I5)", () => {
  it("a consulta escolhe a carteira e envia carteira_id", async () => {
    const { usuario, api } = await montarLogado("ana@alfa.demo");
    const contexto = await screen.findByLabelText("Contexto da consulta");
    expect(within(contexto).getAllByRole("option").map((o) => o.textContent)).toEqual([
      "Sem carteira",
      "Homologação 2026 · Homologação",
    ]);
    await usuario.selectOptions(contexto, "cart-1");
    await usuario.type(screen.getByLabelText("Pergunta em linguagem natural"), "Resumo do CNPJ 99.999.999/0001-91");
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));
    await waitFor(() =>
      expect(api.consultas.criar).toHaveBeenCalledWith({ pergunta: "Resumo do CNPJ 99.999.999/0001-91", carteira_id: "cart-1" }),
    );
  });

  it("sem carteira escolhida, não manda carteira_id", async () => {
    const { usuario, api } = await montarLogado("ana@alfa.demo");
    await screen.findByLabelText("Contexto da consulta");
    await usuario.type(screen.getByLabelText("Pergunta em linguagem natural"), "Resumo do CNPJ 99.999.999/0001-91");
    await usuario.click(screen.getByRole("button", { name: "Consultar" }));
    await waitFor(() => expect(api.consultas.criar).toHaveBeenCalledWith({ pergunta: "Resumo do CNPJ 99.999.999/0001-91" }));
  });

  it("a fila abre a consulta já com a carteira e a pergunta sobre o fornecedor", async () => {
    const { usuario } = await montarLogado("ana@alfa.demo", "/carteiras/cart-1");
    const [primeiro] = await screen.findAllByRole("listitem", { name: /fornecedor/i });
    await usuario.click(within(primeiro).getByRole("link", { name: /Perguntar sobre este fornecedor/ }));
    expect(await screen.findByLabelText("Pergunta em linguagem natural")).toHaveValue(
      "Qual o resumo do fornecedor 99.999.999/0001-91?",
    );
    expect(await screen.findByLabelText("Contexto da consulta")).toHaveValue("cart-1");
  });

  it("o recibo mostra a carteira e a finalidade usadas como contexto", async () => {
    const comCarteira = { ...RECIBO_ANA, conteudo: { ...RECIBO_ANA.conteudo, carteira: { id: "cart-1", finalidade: "homologacao" } } };
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1", apiFalsa({ recibo: async () => comCarteira }));
    await screen.findByRole("heading", { name: "Recibo de evidências" });
    expect(await screen.findByText("Carteira com finalidade Homologação")).toBeInTheDocument();
  });
});

describe("02 recibo: o que o SPEC §12 lista", () => {
  const conteudo = RECIBO_ANA.conteudo;

  it("mostra plano e parâmetros, fontes com a coleta e como a resposta foi produzida", async () => {
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1");
    const plano = await screen.findByRole("region", { name: "Plano e parâmetros" });
    expect(plano).toHaveTextContent("Contratos vencendo");
    expect(plano).toHaveTextContent("contratos_vencendo@v1");
    expect(plano).toHaveTextContent("CNPJ99.999.999/0001-91");
    expect(plano).toHaveTextContent("Prazo em dias180");
    expect(plano).toHaveTextContent("Data de referência06/11/2026");
    expect(plano).toHaveTextContent("Estados consultadosPE");

    const fontes = screen.getByRole("region", { name: "Fontes" });
    expect(fontes).toHaveTextContent("TCE-PE Dados Abertos");
    expect(fontes).toHaveTextContent("coletada em 06/11/2026");

    const producao = screen.getByRole("region", { name: "Como a resposta foi produzida" });
    expect(producao).toHaveTextContent("Planoregras do sistema, sem IA");
    expect(producao).toHaveTextContent("Textoaprovado pelo verificador");
    expect(producao).toHaveTextContent("planejador_v1");
  });

  it("resposta padrão mostra o motivo em português e o modelo que planejou", async () => {
    const recibo = {
      ...RECIBO_ANA,
      conteudo: {
        ...conteudo,
        verificacao: { status: "fallback" as const, motivos: ["numero_fora_do_resultado", "motivo_novo"] },
        ia: { provedor: "gemini", modelo: "gemini-3.6-flash", versao_prompt_planejador: "planejador_v1",
          versao_prompt_redator: "redator_v2", planejador_por_regras: false },
      },
    };
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1", apiFalsa({ recibo: async () => recibo }));
    const producao = await screen.findByRole("region", { name: "Como a resposta foi produzida" });
    expect(producao).toHaveTextContent("Planomodelo gemini-3.6-flash");
    expect(producao).toHaveTextContent("resposta padrão do sistema, com os valores do banco");
    expect(producao).toHaveTextContent("o texto da IA trazia um número que não estava no resultado");
    expect(producao).toHaveTextContent("motivo_novo"); // motivo sem tradução aparece como veio
    expect(producao).toHaveTextContent("redator_v2");
  });

  it("consulta sem valor em reais destaca a contagem principal", async () => {
    const recibo = {
      ...RECIBO_ANA,
      conteudo: {
        ...conteudo,
        valores: {
          v1: { valor: "99.999.999/0001-91", tipo: "texto" as const, origem: "parametros.cnpj", significado: "CNPJ do fornecedor" },
          v2: { valor: "2", tipo: "inteiro" as const, origem: "count(sancoes)", significado: "número de sanções registradas" },
          v3: { valor: "1", tipo: "inteiro" as const, origem: "count(sancoes vigentes)", significado: "número de sanções vigentes" },
        },
      },
    };
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1", apiFalsa({ recibo: async () => recibo }));
    const destaque = await screen.findByRole("region", { name: "Número de sanções registradas" });
    expect(destaque).toHaveTextContent("2");
    expect(screen.queryByText("Sem valor em reais")).not.toBeInTheDocument();
  });

  it("link de origem fora de http(s) vira texto", async () => {
    const linhas = [{ ...conteudo.linhas[0], url_origem: "javascript:alert(1)" }];
    const recibo = { ...RECIBO_ANA, conteudo: { ...conteudo, linhas } };
    await montarLogado("ana@alfa.demo", "/recibos/recibo-1", apiFalsa({ recibo: async () => recibo }));
    const tabela = await screen.findByRole("table");
    expect(within(tabela).queryByRole("link")).not.toBeInTheDocument();
    expect(tabela).toHaveTextContent("Registro 01 · sem link público");
  });

  it("copia o selo e avisa em texto", async () => {
    const { usuario } = await montarLogado("ana@alfa.demo", "/recibos/recibo-1");
    await usuario.click(await screen.findByRole("button", { name: "Copiar selo" }));
    expect(await screen.findByText("Selo copiado")).toBeInTheDocument();
    expect(await navigator.clipboard.readText()).toBe(RECIBO_ANA.hash);
  });
});

describe("02 recibo: âncora na trilha de auditoria", () => {
  const evento = (recibo_hash: string) => ({
    seq: 41, usuario_id: "u", evento: "consulta", criado_em: "2026-11-06T11:12:00Z", hash: "9".repeat(64),
    detalhes: { recibo_id: "recibo-1", recibo_hash },
  });

  it("auditor vê que o selo do recibo é o mesmo gravado na trilha", async () => {
    const api = apiFalsa({ eventos: async () => [evento(RECIBO_ANA.hash)] });
    await montarLogado("caio@alfa.demo", "/recibos/recibo-1", api);
    const selo = await screen.findByRole("status", { name: "Âncora na trilha de auditoria" });
    await waitFor(() => expect(selo).toHaveTextContent("Ancorado na trilha de auditoria · evento #41"));
    // O hash do recibo fica no evento da consulta respondida ou da abstenção: lê os dois, no teto do contrato.
    expect(api.auditoria.listar).toHaveBeenCalledWith(500, "consulta");
    expect(api.auditoria.listar).toHaveBeenCalledWith(500, "abstencao");
  });

  it("recibo de uma abstenção também acha a âncora", async () => {
    const abstencao = { ...evento(RECIBO_ANA.hash), seq: 57, evento: "abstencao" };
    const api = apiFalsa();
    api.auditoria.listar = vi.fn(async (_limite?: number, tipo?: string) => (tipo === "abstencao" ? [abstencao] : []));
    await montarLogado("caio@alfa.demo", "/recibos/recibo-1", api);
    const selo = await screen.findByRole("status", { name: "Âncora na trilha de auditoria" });
    await waitFor(() => expect(selo).toHaveTextContent("Ancorado na trilha de auditoria · evento #57"));
  });

  it("selo diferente do gravado na trilha aparece como divergência", async () => {
    const api = apiFalsa({ eventos: async () => [evento("f".repeat(64))] });
    await montarLogado("caio@alfa.demo", "/recibos/recibo-1", api);
    const selo = await screen.findByRole("status", { name: "Âncora na trilha de auditoria" });
    await waitFor(() => expect(selo).toHaveTextContent("O selo do recibo não confere com a trilha de auditoria"));
  });

  it("recibo sem evento entre os recentes diz isso, sem acusar alteração", async () => {
    await montarLogado("caio@alfa.demo", "/recibos/recibo-1");
    const selo = await screen.findByRole("status", { name: "Âncora na trilha de auditoria" });
    await waitFor(() =>
      expect(selo).toHaveTextContent("Âncora na trilha não localizada entre as 500 respostas e 500 abstenções mais recentes"),
    );
  });

  it("analista não consulta a trilha (a API responderia 403 e registraria a negação)", async () => {
    const { api } = await montarLogado("ana@alfa.demo", "/recibos/recibo-1");
    await screen.findByRole("status", { name: "Integridade do recibo" });
    expect(screen.queryByRole("status", { name: "Âncora na trilha de auditoria" })).not.toBeInTheDocument();
    expect(api.auditoria.listar).not.toHaveBeenCalled();
  });
});
