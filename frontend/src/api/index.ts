// Interface da API usada pelas telas. Telas nunca chamam fetch: recebem uma `Api` pelo ApiProvider.
// Isso permite trocar a implementação (real, simulada, de teste) sem tocar nas telas.
// Tela nova = um módulo novo aqui (ex.: recibos, carteiras) + um campo em `Api`.

import { consultasSimuladas } from "./adaptadores/consultasSimuladas";
import type { Http } from "./http";
import type { ConsultaEntrada, ConsultaSaida, LoginEntrada, LoginSaida, Usuario } from "./types";

export interface ApiAuth {
  login(entrada: LoginEntrada): Promise<LoginSaida>;
  me(): Promise<Usuario>;
}

export interface ApiConsultas {
  criar(entrada: ConsultaEntrada): Promise<ConsultaSaida>;
}

export interface Api {
  auth: ApiAuth;
  consultas: ApiConsultas;
}

export function criarApiAuth(http: Http): ApiAuth {
  return {
    login: (entrada) => http.post<LoginSaida>("/auth/login", entrada),
    me: () => http.get<Usuario>("/me"),
  };
}

export function criarApiConsultas(http: Http): ApiConsultas {
  return {
    criar: (entrada) => http.post<ConsultaSaida>("/consultas", entrada),
  };
}

export interface OpcoesApi {
  /** Troca POST /consultas pelo adaptador simulado (até a T11 ficar pronta). */
  consultasSimuladas?: boolean;
}

export function criarApi(http: Http, opcoes: OpcoesApi = {}): Api {
  return {
    auth: criarApiAuth(http),
    consultas: opcoes.consultasSimuladas ? consultasSimuladas() : criarApiConsultas(http),
  };
}
