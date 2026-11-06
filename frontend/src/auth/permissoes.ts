// Matriz de perfis (SPEC §6.2), só para a interface decidir o que mostrar.
// Não é controle de acesso: o backend recusa de qualquer jeito (403) e registra na auditoria.

import type { Perfil } from "../api/types";

export type Acao = "consultar" | "ver_auditoria" | "editar_carteira" | "ver_historico";

const MATRIZ: Record<Acao, readonly Perfil[]> = {
  consultar: ["analista", "admin"],
  ver_auditoria: ["auditor", "admin"],
  editar_carteira: ["analista", "admin"],
  // GET /consultas: próprias (analista, admin) ou do tenant (auditor, admin). Gestor recebe 403.
  ver_historico: ["analista", "auditor", "admin"],
};

export function pode(perfil: Perfil | undefined, acao: Acao): boolean {
  return perfil !== undefined && MATRIZ[acao].includes(perfil);
}
