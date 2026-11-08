import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { Provedores } from "../Provedores";
import type { Api } from "../api";
import { ErroApi } from "../api/http";
import type {
  CarteiraCriada,
  CarteiraEntrada,
  CarteiraListada,
  ConsultaListada,
  ConsultaSaida,
  Dossie,
  EventoAuditoria,
  ExecucaoIngestao,
  Fila,
  Fonte,
  Metricas,
  Recibo,
  Usuario,
  VerificacaoCadeia,
  VerificacaoRecibo,
} from "../api/types";
import { criarSessao, type ArmazenamentoToken } from "../auth/sessao";
import { FUTURO_ROUTER } from "../config/ambiente";

export const ANA: Usuario = {
  id: "00000000-0000-0000-0000-0000000000a1",
  nome: "Ana (analista)",
  perfil: "analista",
  tenant: { id: "00000000-0000-0000-0000-00000000a1fa", nome: "Cliente Alfa" },
  ufs: ["PE"],
};

export const GIL: Usuario = { ...ANA, id: "00000000-0000-0000-0000-0000000000a3", nome: "Gil (gestor)", perfil: "gestor" };

const RESPOSTA_ANA_TEXTO =
  "O fornecedor tem 2 contratos vigentes em PE, que somam R$ 1.250.000,00 [1], até 14/01/2027 [2].";

export const RESPOSTA_ANA: ConsultaSaida = {
  consulta_id: "c-1",
  status: "respondida",
  resposta: RESPOSTA_ANA_TEXTO,
  citacoes: [
    {
      n: 1,
      tabela: "contratos",
      id: "linha-1",
      fonte_id: "pe_portal",
      url_origem: "https://sistemas.tcepe.tc.br/DadosAbertos/Contratos!json?AnoReferencia=2025",
      coletado_em: "2026-11-06T09:00:00Z",
    },
    { n: 2, tabela: "contratos", id: "linha-2", fonte_id: "pe_portal", url_origem: null, coletado_em: "2026-11-06T09:00:00Z" },
  ],
  recibo_id: "recibo-1",
  sintetico: false,
};

export const CAIO: Usuario = { ...ANA, id: "00000000-0000-0000-0000-0000000000a2", nome: "Caio (auditor)", perfil: "auditor" };

/** Recibo de RESPOSTA_ANA, no formato de contracts/recibo.schema.json. */
export const RECIBO_ANA: Recibo = {
  id: "recibo-1",
  hash: "a".repeat(64),
  criado_em: "2026-11-06T11:12:00Z",
  conteudo: {
    versao: "v1",
    consulta_id: "c-1",
    perfil: "analista",
    ufs_autorizadas: ["PE"],
    pergunta: "Quais contratos do CNPJ 99.999.999/0001-91 vencem nos próximos 6 meses?",
    plano: { intent: "contratos_vencendo", parametros: { cnpj: "99999999000191", dias: 180 } },
    execucao: {
      consulta_catalogo: "contratos_vencendo@v1",
      parametros_efetivos: { cnpj: "99999999000191", dias: 180, hoje: "2026-11-06", ufs: ["PE"] },
      ufs_efetivas: ["PE"],
      n_linhas: 2,
      duracao_ms: 12,
    },
    linhas: [
      {
        tabela: "contratos",
        id: "linha-1",
        fonte_id: "pe_portal",
        id_origem: "ctr:2025:001",
        url_origem: "https://sistemas.tcepe.tc.br/DadosAbertos/Contratos!json?AnoReferencia=2025",
        coletado_em: "2026-11-06T09:00:00Z",
        hash_conteudo: "b".repeat(64),
      },
      {
        tabela: "contratos",
        id: "linha-2",
        fonte_id: "pe_portal",
        id_origem: "ctr:2025:002",
        url_origem: null,
        coletado_em: "2026-11-06T09:00:00Z",
        hash_conteudo: "c".repeat(64),
      },
    ],
    valores: {
      v1: { valor: "99.999.999/0001-91", tipo: "texto", origem: "parametros.cnpj" },
      v4: { valor: "1250000.00", tipo: "moeda", origem: "sum(valor_global)" },
    },
    fontes: [
      { fonte_id: "pe_portal", nome: "TCE-PE Dados Abertos", coletado_em: "2026-11-06T09:00:00Z", execucao_id: null, sintetico: false },
    ],
    resposta_final: RESPOSTA_ANA_TEXTO,
    verificacao: { status: "aprovado", motivos: [] },
    ia: { provedor: "mock", versao_prompt_planejador: "planejador_v1", planejador_por_regras: true },
    criado_em: "2026-11-06T11:12:00Z",
  },
};

export const FONTES: Fonte[] = [
  { id: "pncp", nome: "Portal Nacional de Contratações Públicas", tipo: "api",
    ultima_execucao: { id: "e1", status: "ok", finalizada_em: "2026-11-06T12:00:00Z", registros_novos: 1234 } },
  { id: "ceis", nome: "Cadastro de Empresas Inidôneas e Suspensas", tipo: "arquivo",
    ultima_execucao: { id: "e2", status: "ok", finalizada_em: "2026-11-06T12:05:00Z", registros_novos: 14604 } },
  { id: "pe_portal", nome: "TCE-PE Dados Abertos", tipo: "api", ultima_execucao: null },
  { id: "demo_sintetico", nome: "Dados sintéticos de demonstração", tipo: "sintetico", ultima_execucao: null },
];

export const HISTORICO: ConsultaListada[] = [
  { id: "c1000000-0000-0000-0000-000000000001", usuario_id: ANA.id, carteira_id: null, pergunta: "Resumo do CNPJ X",
    intent: "resumo_fornecedor", status: "respondida", criada_em: "2026-11-06T11:12:00Z", recibo_id: "recibo-1" },
  { id: "c2000000-0000-0000-0000-000000000002", usuario_id: ANA.id, carteira_id: null, pergunta: "Quanto recebeu em Alagoas?",
    intent: "resumo_fornecedor", status: "negada", criada_em: "2026-11-06T11:13:00Z", recibo_id: null },
  { id: "c3000000-0000-0000-0000-000000000003", usuario_id: "outro", carteira_id: null, pergunta: "Previsão do tempo",
    intent: "fora_de_escopo", status: "abstencao", criada_em: "2026-11-06T11:15:00Z", recibo_id: null },
];

export const EXECUCOES: ExecucaoIngestao[] = [
  { id: "e2", fonte_id: "ceis", status: "ok", iniciada_em: "2026-11-06T12:04:00Z", finalizada_em: "2026-11-06T12:05:00Z",
    registros_lidos: 14700, registros_novos: 14604, registros_descartados: 96, erro: null },
  { id: "e3", fonte_id: "pncp", status: "falhou", iniciada_em: "2026-11-06T11:00:00Z", finalizada_em: "2026-11-06T11:01:00Z",
    registros_lidos: 0, registros_novos: 0, registros_descartados: 0, erro: "FonteIndisponivel: 503 depois de 3 tentativas" },
];

export const METRICAS: Metricas = {
  eval: { gerado_em: "2026-11-08T05:53:39+00:00", provedor_llm: "mock", n_casos: 100, ok: 100, acerto_intent: 100,
    n_intent_avaliada: 80, meta_intent: 90, acerto_comportamento: 100, acerto_resultado: 100, n_com_sql_referencia: 1,
    citacao_correta: 100, n_com_citacao: 42, taxa_fallback: 0 },
  ataques: { gerado_em: "2026-11-08T06:10:00+00:00", provedor_llm: "mock", n_casos: 50, bloqueados: 49,
    pct_bloqueado: 98, vazamentos: 0,
    por_categoria: { direta: { n: 20, bloqueados: 20, vazamentos: 0 }, escopo: { n: 30, bloqueados: 29, vazamentos: 0 } } },
  cronometro: null,
  ultima_atualizacao: "2026-11-08T06:10:00+00:00",
};

export const CARTEIRAS: CarteiraListada[] = [
  { id: "cart-1", nome: "Homologação 2026", finalidade: "homologacao", n_itens: 2, criada_em: "2026-11-05T10:00:00Z" },
];

export const FILA: Fila = {
  carteira: { id: "cart-1", nome: "Homologação 2026", finalidade: "homologacao", criada_em: "2026-11-05T10:00:00Z" },
  itens: [
    {
      cnpj: "99999999000191",
      razao_social: "FORNECEDOR ALFA LTDA",
      prioridade: 61.5,
      valor_exposto: "1250000.00",
      sinais: [
        {
          tipo: "sancao_direta",
          gravidade: "forte",
          explicacao: "Sanção vigente no CEIS até 10/05/2027.",
          evidencias: [{ tabela: "sancoes", id: "s-1", url_origem: "https://portaldatransparencia.gov.br/sancoes/ceis/1" }],
        },
        {
          tipo: "penhasco",
          gravidade: "atencao",
          explicacao: "62% do valor vigente termina em até 180 dias.",
          evidencias: [{ tabela: "contratos", id: "ct-1", url_origem: null }],
        },
      ],
    },
    { cnpj: "11222333000181", razao_social: null, prioridade: 0, valor_exposto: "0.00", sinais: [] },
  ],
};

export const DOSSIE: Dossie = {
  fornecedor: { cnpj: "99999999000191", razao_social: "FORNECEDOR ALFA LTDA", uf_sede: "PE" },
  resumo_por_uf: [
    { uf: "PE", n_contratos: 3, valor_contratado: "1800000.00", valor_vigente: "1250000.00", n_pagamentos: 4,
      valor_pago: "300000.00", valor_empenhado: "450000.00" },
  ],
  contratos_vigentes: [
    { id: "ct-1", fonte_id: "pe_portal", id_origem: "ctr:2025:001",
      url_origem: "https://sistemas.tcepe.tc.br/DadosAbertos/Contratos!json?AnoReferencia=2025",
      coletado_em: "2026-11-06T09:00:00Z", uf: "PE", orgao_id: "o-1", orgao_nome: "Secretaria de Saúde",
      objeto: "Limpeza hospitalar", valor_global: "1250000.00", data_assinatura: "2025-01-10",
      vigencia_inicio: "2025-01-15", vigencia_fim: "2027-01-14" },
  ],
  vencendo_180d: [],
  sancoes: [
    { id: "s-1", fonte_id: "ceis", id_origem: "ceis:1", url_origem: "https://portaldatransparencia.gov.br/sancoes/ceis/1",
      coletado_em: "2026-11-06T08:00:00Z", tipo: "Impedimento", orgao_sancionador: "Prefeitura do Recife",
      uf_orgao: "PE", data_inicio: "2026-05-10", data_fim: "2027-05-10", fundamentacao: null, vigente: true },
  ],
  sinais: [
    { id: "si-1", tipo: "sancao_direta", gravidade: "forte", uf: "PE", valor: null,
      explicacao: "Sanção vigente no CEIS até 10/05/2027.",
      evidencias: [{ tabela: "sancoes", id: "s-1", url_origem: "https://portaldatransparencia.gov.br/sancoes/ceis/1" }],
      versao_regra: "v1", calculado_em: "2026-11-06T10:00:00Z" },
  ],
  socios: [{ socio_tipo: "PF", socio_exibicao: "***.456.789-** JOSÉ", fonte_id: "receita_qsa", coletado_em: "2026-11-06T07:00:00Z" }],
  fontes: [
    { fonte_id: "pe_portal", nome: "TCE-PE Dados Abertos", coletado_em: "2026-11-06T09:00:00Z", sintetico: false },
    { fonte_id: "ceis", nome: "CEIS", coletado_em: "2026-11-06T08:00:00Z", sintetico: false },
  ],
};

export const EVENTOS: EventoAuditoria[] = [
  { seq: 12, usuario_id: ANA.id, evento: "consulta", detalhes: { intent: "resumo_fornecedor" },
    criado_em: "2026-11-06T11:12:00Z", hash: "d".repeat(64) },
  { seq: 11, usuario_id: ANA.id, evento: "negado", detalhes: { motivo: "uf_fora_do_escopo" },
    criado_em: "2026-11-06T11:10:00Z", hash: "e".repeat(64) },
];

export const CADEIA_INTEGRA: VerificacaoCadeia = { integra: true, n_eventos: 12, primeiro_seq_quebrado: null };

export const RECIBO_INTEGRO: VerificacaoRecibo = { integro: true, hash_gravado: "a".repeat(64), hash_recalculado: "a".repeat(64) };

/** Backend falso: usuários por e-mail (senha demo123), resposta de consulta configurável. */
export function apiFalsa(
  opcoes: {
    usuarios?: Record<string, Usuario>;
    consulta?: () => Promise<ConsultaSaida>;
    recibo?: (id: string) => Promise<Recibo>;
    historico?: () => Promise<ConsultaListada[]>;
    verificarRecibo?: (id: string) => Promise<VerificacaoRecibo>;
    criarCarteira?: (entrada: CarteiraEntrada) => Promise<CarteiraCriada>;
    fila?: (id: string) => Promise<Fila>;
    dossie?: (cnpj: string) => Promise<Dossie>;
    cadeia?: () => Promise<VerificacaoCadeia>;
    metricas?: () => Promise<Metricas>;
  } = {},
) {
  const usuarios = opcoes.usuarios ?? { "ana@alfa.demo": ANA, "gil@alfa.demo": GIL, "caio@alfa.demo": CAIO };
  let atual: Usuario | null = null;
  const api: Api = {
    auth: {
      login: vi.fn(async ({ email, senha }) => {
        const usuario = usuarios[email];
        if (!usuario || senha !== "demo123") throw new ErroApi(401, "NAO_AUTENTICADO", "E-mail ou senha inválidos.", "rid-1");
        atual = usuario;
        return { token: `token-${email}`, usuario };
      }),
      me: vi.fn(async () => {
        if (!atual) throw new ErroApi(401, "NAO_AUTENTICADO", "Autenticação necessária.");
        return atual;
      }),
    },
    consultas: {
      criar: vi.fn(opcoes.consulta ?? (async () => RESPOSTA_ANA)),
      listar: vi.fn(opcoes.historico ?? (async () => HISTORICO)),
    },
    fontes: { listar: vi.fn(async () => FONTES), execucoes: vi.fn(async () => EXECUCOES) },
    metricas: { obter: vi.fn(opcoes.metricas ?? (async () => METRICAS)) },
    recibos: {
      obter: vi.fn(
        opcoes.recibo ??
          (async (id: string) => {
            if (id !== RECIBO_ANA.id) throw new ErroApi(404, "NAO_ENCONTRADO", "Recibo não encontrado.", "rid-404");
            return RECIBO_ANA;
          }),
      ),
      verificar: vi.fn(opcoes.verificarRecibo ?? (async () => RECIBO_INTEGRO)),
    },
    carteiras: {
      listar: vi.fn(async () => CARTEIRAS),
      criar: vi.fn(
        opcoes.criarCarteira ??
          (async (e: CarteiraEntrada) => ({ id: "cart-nova", nome: e.nome, finalidade: e.finalidade, n_itens: e.cnpjs.length, cnpjs_invalidos: [] })),
      ),
      fila: vi.fn(
        opcoes.fila ??
          (async (id: string) => {
            if (id !== FILA.carteira.id) throw new ErroApi(404, "NAO_ENCONTRADO", "Carteira não encontrada.", "rid-404");
            return FILA;
          }),
      ),
    },
    fornecedores: { dossie: vi.fn(opcoes.dossie ?? (async () => DOSSIE)) },
    auditoria: {
      listar: vi.fn(async () => EVENTOS),
      verificar: vi.fn(opcoes.cadeia ?? (async () => CADEIA_INTEGRA)),
    },
  };
  return api;
}

export function tokenEmMemoria(inicial: string | null = null): ArmazenamentoToken {
  let token = inicial;
  return {
    ler: () => token,
    gravar: (t) => {
      token = t;
    },
    apagar: () => {
      token = null;
    },
  };
}

export function montarApp({ api = apiFalsa(), rota = "/", token = tokenEmMemoria() } = {}) {
  const sessao = criarSessao(token);
  const resultado = render(
    <MemoryRouter initialEntries={[rota]} future={FUTURO_ROUTER}>
      <Provedores api={api} sessao={sessao}>
        <App />
      </Provedores>
    </MemoryRouter>,
  );
  return { ...resultado, api, sessao, token };
}
