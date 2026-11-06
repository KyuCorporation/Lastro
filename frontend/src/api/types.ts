// Espelha contracts/api.md (v1, congelado). Mudou o contrato? Mude aqui e em nenhum outro lugar.
// Dinheiro chega como string decimal ("1234.56"); datas em ISO 8601.

export type Perfil = "analista" | "gestor" | "auditor" | "admin";

export type CodigoErro =
  | "NAO_AUTENTICADO"
  | "PERFIL_SEM_PERMISSAO"
  | "ESCOPO_NEGADO"
  | "NAO_ENCONTRADO"
  | "ENTRADA_INVALIDA"
  | "LIMITE_EXCEDIDO"
  | "FONTE_INDISPONIVEL"
  | "ERRO_INTERNO";

export interface CorpoErro {
  erro: { codigo: CodigoErro | string; mensagem: string; request_id: string };
}

export interface Tenant {
  id: string;
  nome: string;
}

/** GET /me. O login devolve o mesmo formato em `usuario`. */
export interface Usuario {
  id: string;
  nome: string;
  perfil: Perfil;
  tenant: Tenant;
  ufs: string[];
}

export interface LoginEntrada {
  email: string;
  senha: string;
}

export interface LoginSaida {
  token: string;
  usuario: Usuario;
}

export type StatusConsulta = "respondida" | "abstencao" | "esclarecimento" | "negada" | "erro";

export type TabelaCitada = "contratos" | "pagamentos" | "sancoes" | "sinais" | "socios";

export interface Citacao {
  n: number;
  tabela: TabelaCitada | string;
  id: string;
  fonte_id: string;
  url_origem: string | null;
  coletado_em: string;
}

/** POST /consultas: pergunta com até 500 caracteres. */
export interface ConsultaEntrada {
  pergunta: string;
  carteira_id?: string;
}

export interface ConsultaSaida {
  consulta_id: string;
  status: StatusConsulta;
  resposta: string;
  citacoes: Citacao[];
  recibo_id: string | null;
  sintetico: boolean;
}

export const LIMITE_PERGUNTA = 500;
