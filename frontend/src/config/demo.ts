// Usuários do seed de desenvolvimento (SPEC §6.3, db/seeds/010_demo_usuarios.sql).
// Só aparecem com VITE_DEMO_MODE=true. A senha é a pública do seed, nunca uma credencial real.

import type { Perfil } from "../api/types";

export const SENHA_SEED_DEMO = "demo123";

export interface UsuarioDemo {
  email: string;
  nome: string;
  perfil: Perfil;
  tenant: string;
  ufs: string[];
}

export const USUARIOS_DEMO: UsuarioDemo[] = [
  { email: "ana@alfa.demo", nome: "Ana", perfil: "analista", tenant: "Cliente Alfa", ufs: ["PE"] },
  { email: "bia@beta.demo", nome: "Bia", perfil: "analista", tenant: "Cliente Beta", ufs: ["AL"] },
  { email: "admin@alfa.demo", nome: "Admin", perfil: "admin", tenant: "Cliente Alfa", ufs: ["PE", "AL"] },
  { email: "caio@alfa.demo", nome: "Caio", perfil: "auditor", tenant: "Cliente Alfa", ufs: ["PE"] },
  { email: "gil@alfa.demo", nome: "Gil", perfil: "gestor", tenant: "Cliente Alfa", ufs: ["PE"] },
];
