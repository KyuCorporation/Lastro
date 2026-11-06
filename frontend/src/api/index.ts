// Interface da API usada pelas telas. Telas nunca chamam fetch: recebem uma `Api` pelo ApiProvider.
// Isso permite trocar a implementação (real, simulada, de teste) sem tocar nas telas.
// Tela nova = um módulo novo aqui (ex.: carteiras) + um campo em `Api`.

import { consultasSimuladas } from "./adaptadores/consultasSimuladas";
import type { Http } from "./http";
import type {
  ConsultaEntrada,
  ConsultaListada,
  ConsultaSaida,
  Fonte,
  LoginEntrada,
  LoginSaida,
  Recibo,
  Usuario,
} from "./types";

export interface ApiAuth {
  login(entrada: LoginEntrada): Promise<LoginSaida>;
  me(): Promise<Usuario>;
}

export interface ApiConsultas {
  criar(entrada: ConsultaEntrada): Promise<ConsultaSaida>;
  /** GET /consultas: histórico visível pela RLS. */
  listar(limite?: number): Promise<ConsultaListada[]>;
}

export interface ApiRecibos {
  obter(id: string): Promise<Recibo>;
}

export interface ApiFontes {
  listar(): Promise<Fonte[]>;
}

export interface Api {
  auth: ApiAuth;
  consultas: ApiConsultas;
  recibos: ApiRecibos;
  fontes: ApiFontes;
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
    listar: (limite = 50) => http.get<ConsultaListada[]>(`/consultas?limite=${encodeURIComponent(limite)}`),
  };
}

export function criarApiRecibos(http: Http): ApiRecibos {
  return {
    obter: (id) => http.get<Recibo>(`/recibos/${encodeURIComponent(id)}`),
  };
}

export function criarApiFontes(http: Http): ApiFontes {
  return { listar: () => http.get<Fonte[]>("/fontes") };
}

export interface OpcoesApi {
  /** Troca POST /consultas pelo adaptador simulado (só para desenvolver a tela sem backend). */
  consultasSimuladas?: boolean;
}

export function criarApi(http: Http, opcoes: OpcoesApi = {}): Api {
  return {
    auth: criarApiAuth(http),
    consultas: opcoes.consultasSimuladas ? consultasSimuladas() : criarApiConsultas(http),
    recibos: criarApiRecibos(http),
    fontes: criarApiFontes(http),
  };
}
