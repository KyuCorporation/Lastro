// Rótulos de exibição. Só texto: nenhuma regra de acesso mora aqui.

import type { Finalidade, Gravidade, Perfil, StatusConsulta } from "../api/types";

export const NOME_PERFIL: Record<Perfil, string> = {
  analista: "Analista de risco",
  gestor: "Gestor de contrato",
  auditor: "Auditor",
  admin: "Administrador",
};

const NOME_UF: Record<string, string> = {
  AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal",
  ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul",
  MT: "Mato Grosso", PA: "Pará", PB: "Paraíba", PE: "Pernambuco", PI: "Piauí", PR: "Paraná",
  RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia", RR: "Roraima", RS: "Rio Grande do Sul",
  SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins",
};

export function nomeUf(uf: string): string {
  return NOME_UF[uf] ?? uf;
}

/** "Pernambuco" ou "Alagoas e Pernambuco". */
export function nomesUfs(ufs: string[]): string {
  const nomes = ufs.map(nomeUf);
  return nomes.length <= 1 ? (nomes[0] ?? "Sem estado") : `${nomes.slice(0, -1).join(", ")} e ${nomes.at(-1)}`;
}

export type Tom = "verde" | "vermelho" | "ambar" | "neutro";

/** Como cada desfecho de consulta aparece (texto sempre presente: nada depende só de cor). */
export const STATUS_CONSULTA: Record<StatusConsulta, { selo: string; resultado: string; tom: Tom }> = {
  respondida: { selo: "Resposta com evidências", resultado: "Respondida", tom: "verde" },
  abstencao: { selo: "Nenhum registro encontrado", resultado: "Sem registros", tom: "ambar" },
  esclarecimento: { selo: "Preciso de um detalhe", resultado: "Esclarecimento", tom: "ambar" },
  negada: { selo: "Acesso negado", resultado: "Bloqueada", tom: "vermelho" },
  erro: { selo: "Não foi possível responder", resultado: "Erro", tom: "vermelho" },
};

const NOME_INTENT: Record<string, string> = {
  resumo_fornecedor: "Resumo do fornecedor",
  contratos_vigentes: "Contratos vigentes",
  contratos_vencendo: "Contratos vencendo",
  pagamentos_periodo: "Pagamentos no período",
  sancoes_fornecedor: "Sanções do fornecedor",
  orgaos_fornecedor: "Órgãos do fornecedor",
  busca_objeto: "Busca por objeto",
  fila_carteira: "Fila da carteira",
  socios_sancionados: "Sócios sancionados",
  fora_de_escopo: "Fora do catálogo",
  esclarecer: "Pedido de detalhe",
};

export function nomeIntent(intent: string | null | undefined): string {
  if (!intent) return "Consulta";
  return NOME_INTENT[intent.split("@")[0]] ?? intent;
}

export const NOME_FINALIDADE: Record<Finalidade, string> = {
  homologacao: "Homologação",
  monitoramento: "Monitoramento",
  renovacao: "Renovação",
};

/** Gravidade do sinal: o texto vem sempre junto da cor. */
export const GRAVIDADE: Record<Gravidade, { rotulo: string; tom: Tom }> = {
  forte: { rotulo: "Forte", tom: "vermelho" },
  atencao: { rotulo: "Atenção", tom: "ambar" },
  info: { rotulo: "Informativo", tom: "neutro" },
};

const NOME_SINAL: Record<string, string> = {
  sancao_direta: "Sanção vigente",
  penhasco: "Vencimentos concentrados",
  concentracao: "Concentração em um órgão",
  contagio: "Sócio em comum com empresa sancionada",
  liquidez: "Liquidez",
};

export function nomeSinal(tipo: string): string {
  return NOME_SINAL[tipo] ?? tipo;
}

const NOME_EVENTO: Record<string, string> = {
  login: "Login",
  consulta: "Consulta",
  abstencao: "Sem registros",
  negado: "Acesso negado",
  erro: "Erro",
  ataque_detectado: "Tentativa de injeção bloqueada",
  dossie: "Dossiê aberto",
  carteira_criada: "Carteira criada",
  alerta_atualizado: "Alerta atualizado",
  export: "Exportação",
};

export function nomeEvento(evento: string): string {
  return NOME_EVENTO[evento] ?? evento;
}

/** Motivos do verificador (recibo.verificacao.motivos), em português. Motivo novo aparece como veio. */
const NOME_MOTIVO: Record<string, string> = {
  numero_fora_do_resultado: "o texto da IA trazia um número que não estava no resultado",
  uf_fora_do_escopo: "o texto da IA citava um estado fora do seu acesso",
  url_fora_do_resultado: "o texto da IA trazia um link ou e-mail",
  vazamento: "o texto da IA falava das próprias instruções",
  linguagem_de_acusacao: "o texto da IA usava linguagem de acusação",
  contradiz_resultado: "o texto da IA negava registros que o resultado tem",
  sem_valor_do_resultado: "o texto da IA não usava nenhum valor do resultado",
  marcador_fora_de_contexto: "o texto da IA usou um valor com o sentido trocado",
  marcador_desconhecido: "o texto da IA pedia um valor que não existe no resultado",
  marcador_malformado: "o texto da IA veio com a marcação de valor quebrada",
  caractere_nao_permitido: "o texto da IA trazia caractere invisível ou de outro alfabeto",
  texto_longo: "o texto da IA passou do tamanho permitido",
  texto_vazio: "a IA não devolveu texto",
  provedor_indisponivel: "o serviço de IA estava fora do ar",
  erro_provedor: "o serviço de IA falhou",
  tempo_esgotado: "a IA demorou além do limite",
  resultado_vazio: "a consulta não encontrou registros",
  intent_sem_consulta: "esse tipo de consulta ainda não está disponível",
  fora_de_escopo: "a pergunta está fora do catálogo de consultas",
};

export function nomeMotivo(motivo: string): string {
  return NOME_MOTIVO[motivo] ?? motivo;
}
