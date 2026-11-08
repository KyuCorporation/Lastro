// Interface da API usada pelas telas. Telas nunca chamam fetch: recebem uma `Api` pelo ApiProvider.
// Isso permite trocar a implementação (real, simulada, de teste) sem tocar nas telas.
// Tela nova = um módulo novo aqui (ex.: carteiras) + um campo em `Api`.

import { consultasSimuladas } from "./adaptadores/consultasSimuladas";
import type { Http } from "./http";
import type {
  CarteiraCriada,
  CarteiraEntrada,
  CarteiraListada,
  ConsultaEntrada,
  ConsultaListada,
  ConsultaSaida,
  Dossie,
  EventoAuditoria,
  ExecucaoIngestao,
  Fila,
  Fonte,
  LoginEntrada,
  LoginSaida,
  Metricas,
  Recibo,
  Usuario,
  VerificacaoCadeia,
  VerificacaoRecibo,
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
  /** GET /recibos/{id}/verificar: recalcula o hash no servidor. */
  verificar(id: string): Promise<VerificacaoRecibo>;
}

export interface ApiCarteiras {
  listar(): Promise<CarteiraListada[]>;
  criar(entrada: CarteiraEntrada): Promise<CarteiraCriada>;
  fila(id: string): Promise<Fila>;
}

export interface ApiFornecedores {
  dossie(cnpj: string): Promise<Dossie>;
}

export interface ApiAuditoria {
  listar(limite?: number): Promise<EventoAuditoria[]>;
  verificar(): Promise<VerificacaoCadeia>;
}

export interface ApiFontes {
  listar(): Promise<Fonte[]>;
  /** GET /fontes/execucoes: todas as fontes, ou só `fonteId`. */
  execucoes(fonteId?: string): Promise<ExecucaoIngestao[]>;
}

export interface ApiMetricas {
  obter(): Promise<Metricas>;
}

export interface Api {
  auth: ApiAuth;
  consultas: ApiConsultas;
  recibos: ApiRecibos;
  fontes: ApiFontes;
  carteiras: ApiCarteiras;
  fornecedores: ApiFornecedores;
  auditoria: ApiAuditoria;
  metricas: ApiMetricas;
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
    verificar: (id) => http.get<VerificacaoRecibo>(`/recibos/${encodeURIComponent(id)}/verificar`),
  };
}

export function criarApiCarteiras(http: Http): ApiCarteiras {
  return {
    listar: () => http.get<CarteiraListada[]>("/carteiras"),
    criar: (entrada) => http.post<CarteiraCriada>("/carteiras", entrada),
    fila: (id) => http.get<Fila>(`/carteiras/${encodeURIComponent(id)}/fila`),
  };
}

export function criarApiFornecedores(http: Http): ApiFornecedores {
  return { dossie: (cnpj) => http.get<Dossie>(`/fornecedores/${encodeURIComponent(cnpj)}/dossie`) };
}

export function criarApiAuditoria(http: Http): ApiAuditoria {
  return {
    listar: (limite = 100) => http.get<EventoAuditoria[]>(`/auditoria?limite=${encodeURIComponent(limite)}`),
    verificar: () => http.get<VerificacaoCadeia>("/auditoria/verificar"),
  };
}

export function criarApiFontes(http: Http): ApiFontes {
  return {
    listar: () => http.get<Fonte[]>("/fontes"),
    execucoes: (fonteId) =>
      http.get<ExecucaoIngestao[]>(fonteId ? `/fontes/execucoes?fonte_id=${encodeURIComponent(fonteId)}` : "/fontes/execucoes"),
  };
}

export function criarApiMetricas(http: Http): ApiMetricas {
  return { obter: () => http.get<Metricas>("/metricas") };
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
    carteiras: criarApiCarteiras(http),
    fornecedores: criarApiFornecedores(http),
    auditoria: criarApiAuditoria(http),
    metricas: criarApiMetricas(http),
  };
}
