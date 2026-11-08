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

/** GET /consultas: o que a RLS mostra (as próprias; auditor e admin veem o tenant). */
export interface ConsultaListada {
  id: string;
  usuario_id: string;
  carteira_id: string | null;
  pergunta: string;
  intent: string | null;
  status: StatusConsulta;
  criada_em: string;
  recibo_id: string | null;
}

export type TipoValor = "moeda" | "data" | "inteiro" | "percentual" | "texto";

/** Conteúdo do recibo (contracts/recibo.schema.json, v1). Só os campos que a interface usa. */
export interface ConteudoRecibo {
  versao: "v1";
  consulta_id: string;
  perfil: Perfil;
  ufs_autorizadas: string[];
  pergunta: string;
  plano: { intent: string; parametros: Record<string, unknown> };
  execucao: {
    consulta_catalogo: string;
    parametros_efetivos: Record<string, unknown>;
    ufs_efetivas: string[];
    n_linhas: number;
    duracao_ms: number;
  };
  linhas: {
    tabela: string;
    id: string;
    fonte_id: string;
    id_origem: string;
    url_origem: string | null;
    coletado_em: string;
    hash_conteudo: string;
  }[];
  valores?: Record<string, { valor: string; tipo: TipoValor; origem?: string }>;
  fontes: { fonte_id: string; nome: string; coletado_em: string; execucao_id: string | null; sintetico?: boolean }[];
  resposta_final: string;
  verificacao: { status: "aprovado" | "fallback" | "abstencao" | "negado"; motivos?: string[] };
  ia: {
    provedor?: string;
    modelo?: string;
    versao_prompt_planejador?: string;
    versao_prompt_redator?: string;
    planejador_por_regras?: boolean;
  };
  criado_em: string;
}

/** GET /fontes */
export interface Fonte {
  id: string;
  nome: string;
  tipo: string;
  ultima_execucao: {
    id: string;
    status: "ok" | "parcial" | "falhou" | string;
    finalizada_em: string | null;
    registros_novos: number | null;
  } | null;
}

/** GET /recibos/{id} */
export interface Recibo {
  id: string;
  conteudo: ConteudoRecibo;
  hash: string;
  criado_em: string;
}

/** GET /recibos/{id}/verificar: `integro=false` quando conteúdo ou hash mudaram depois de gravados. */
export interface VerificacaoRecibo {
  integro: boolean;
  hash_gravado: string;
  hash_recalculado: string;
}

// ------------------------------------------------------------------ carteiras e fila
export type Finalidade = "homologacao" | "monitoramento" | "renovacao";

/** POST /carteiras: CNPJs com ou sem máscara; os inválidos voltam em `cnpjs_invalidos`. */
export interface CarteiraEntrada {
  nome: string;
  finalidade: Finalidade;
  cnpjs: string[];
}

export interface CarteiraCriada {
  id: string;
  nome: string;
  finalidade: Finalidade;
  n_itens: number;
  cnpjs_invalidos: string[];
}

/** GET /carteiras */
export interface CarteiraListada {
  id: string;
  nome: string;
  finalidade: Finalidade;
  n_itens: number;
  criada_em: string;
}

export type Gravidade = "forte" | "atencao" | "info";

/** Linha de origem que sustenta um sinal. */
export interface Evidencia {
  tabela?: string;
  id?: string;
  url_origem?: string | null;
  [campo: string]: unknown;
}

export interface SinalFila {
  tipo: string;
  gravidade: Gravidade;
  explicacao: string;
  evidencias: Evidencia[];
}

export interface ItemFila {
  cnpj: string;
  razao_social: string | null;
  prioridade: number;
  valor_exposto: string;
  sinais: SinalFila[];
}

/** GET /carteiras/{id}/fila: itens já ordenados por prioridade. */
export interface Fila {
  carteira: { id: string; nome: string; finalidade: Finalidade; criada_em: string };
  itens: ItemFila[];
}

// ------------------------------------------------------------------ dossiê
interface Proveniencia {
  id: string;
  fonte_id: string;
  id_origem: string;
  url_origem: string | null;
  coletado_em: string;
}

export interface ContratoDossie extends Proveniencia {
  uf: string;
  orgao_id: string | null;
  orgao_nome: string | null;
  objeto: string | null;
  valor_global: string | null;
  data_assinatura: string | null;
  vigencia_inicio: string | null;
  vigencia_fim: string | null;
}

export interface SancaoDossie extends Proveniencia {
  tipo: string | null;
  orgao_sancionador: string | null;
  uf_orgao: string | null;
  data_inicio: string | null;
  data_fim: string | null;
  fundamentacao: string | null;
  vigente: boolean;
}

export interface SinalDossie {
  id: string;
  tipo: string;
  gravidade: Gravidade;
  uf: string | null;
  valor: string | null;
  explicacao: string;
  evidencias: Evidencia[];
  versao_regra: string;
  calculado_em: string;
}

export interface ResumoUf {
  uf: string;
  n_contratos: number;
  valor_contratado: string;
  valor_vigente: string;
  n_pagamentos: number;
  valor_pago: string;
  valor_empenhado: string;
}

/** GET /fornecedores/{cnpj}/dossie. `socios` é null para o perfil que não vê sócios (gestor). */
export interface Dossie {
  fornecedor: { cnpj: string; razao_social: string | null; uf_sede: string | null };
  resumo_por_uf: ResumoUf[];
  contratos_vigentes: ContratoDossie[];
  vencendo_180d: ContratoDossie[];
  sancoes: SancaoDossie[];
  sinais: SinalDossie[];
  socios: { socio_tipo: "PF" | "PJ"; socio_exibicao: string; fonte_id: string; coletado_em: string }[] | null;
  fontes: { fonte_id: string; nome: string; coletado_em: string; sintetico: boolean }[];
}

// ------------------------------------------------------------------ auditoria
/** GET /auditoria (auditor e admin): eventos encadeados por hash. */
export interface EventoAuditoria {
  seq: number;
  usuario_id: string | null;
  evento: string;
  detalhes: Record<string, unknown> | null;
  criado_em: string;
  hash: string;
}

/** GET /auditoria/verificar */
export interface VerificacaoCadeia {
  integra: boolean;
  n_eventos: number;
  primeiro_seq_quebrado?: number | null;
}
