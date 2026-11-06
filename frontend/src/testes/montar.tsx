import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { Provedores } from "../Provedores";
import type { Api } from "../api";
import { ErroApi } from "../api/http";
import type { ConsultaListada, ConsultaSaida, Fonte, Recibo, Usuario } from "../api/types";
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

/** Backend falso: usuários por e-mail (senha demo123), resposta de consulta configurável. */
export function apiFalsa(
  opcoes: {
    usuarios?: Record<string, Usuario>;
    consulta?: () => Promise<ConsultaSaida>;
    recibo?: (id: string) => Promise<Recibo>;
    historico?: () => Promise<ConsultaListada[]>;
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
    fontes: { listar: vi.fn(async () => FONTES) },
    recibos: {
      obter: vi.fn(
        opcoes.recibo ??
          (async (id: string) => {
            if (id !== RECIBO_ANA.id) throw new ErroApi(404, "NAO_ENCONTRADO", "Recibo não encontrado.", "rid-404");
            return RECIBO_ANA;
          }),
      ),
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
