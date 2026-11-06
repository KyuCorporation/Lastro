import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import App from "../App";
import { Provedores } from "../Provedores";
import type { Api } from "../api";
import { ErroApi } from "../api/http";
import type { ConsultaSaida, Usuario } from "../api/types";
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

export const RESPOSTA_ANA: ConsultaSaida = {
  consulta_id: "c-1",
  status: "respondida",
  resposta: "O fornecedor tem 2 contratos vigentes em PE, que somam R$ 1.250.000,00 [1], até 14/01/2027 [2].",
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

/** Backend falso: usuários por e-mail (senha demo123), resposta de consulta configurável. */
export function apiFalsa(opcoes: { usuarios?: Record<string, Usuario>; consulta?: () => Promise<ConsultaSaida> } = {}) {
  const usuarios = opcoes.usuarios ?? { "ana@alfa.demo": ANA, "gil@alfa.demo": GIL };
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
    consultas: { criar: vi.fn(opcoes.consulta ?? (async () => RESPOSTA_ANA)) },
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
