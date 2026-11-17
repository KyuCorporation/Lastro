// Interface da API usada pelas telas. Telas nunca chamam fetch: recebem uma `Api` pelo ApiProvider.
// Isso permite trocar a implementação (real ou de teste) sem tocar nas telas.
// Tela nova = um módulo novo aqui (ex.: carteiras) + um campo em `Api`.

import type { Http } from "./http";
import type {
  Alerta,
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
  StatusAlerta,
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

export interface ApiAlertas {
  /** GET /alertas: os do tenant, mais recentes primeiro. */
  listar(status?: StatusAlerta): Promise<Alerta[]>;
}

export interface ApiFornecedores {
  dossie(cnpj: string): Promise<Dossie>;
}

export interface ApiAuditoria {
  /** `evento` filtra pelo tipo (consulta, negado, login…), como o `?evento` de GET /auditoria. */
  listar(limite?: number, evento?: string): Promise<EventoAuditoria[]>;
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
  alertas: ApiAlertas;
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

export function criarApiAlertas(http: Http): ApiAlertas {
  return { listar: (status) => http.get<Alerta[]>(status ? `/alertas?status=${encodeURIComponent(status)}` : "/alertas") };
}

export function criarApiFornecedores(http: Http): ApiFornecedores {
  return { dossie: (cnpj) => http.get<Dossie>(`/fornecedores/${encodeURIComponent(cnpj)}/dossie`) };
}

export function criarApiAuditoria(http: Http): ApiAuditoria {
  return {
    listar: (limite = 100, evento?: string) =>
      http.get<EventoAuditoria[]>(
        `/auditoria?limite=${encodeURIComponent(limite)}${evento ? `&evento=${encodeURIComponent(evento)}` : ""}`,
      ),
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

export function criarApi(http: Http): Api {
  return {
    auth: criarApiAuth(http),
    consultas: criarApiConsultas(http),
    recibos: criarApiRecibos(http),
    fontes: criarApiFontes(http),
    carteiras: criarApiCarteiras(http),
    alertas: criarApiAlertas(http),
    fornecedores: criarApiFornecedores(http),
    auditoria: criarApiAuditoria(http),
    metricas: criarApiMetricas(http),
  };
}
