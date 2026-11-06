import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { Carregando } from "../components/Carregando";
import { useAuth } from "./AuthProvider";

/** Só renderiza com usuário autenticado; senão manda para /login guardando de onde veio. */
export function RotaProtegida({ children }: { children: ReactNode }) {
  const { estado } = useAuth();
  const local = useLocation();
  if (estado.status === "verificando") return <Carregando texto="Conferindo sua sessão…" />;
  if (estado.status === "anonimo") {
    return <Navigate to="/login" replace state={{ de: local.pathname, motivo: estado.motivo }} />;
  }
  return <>{children}</>;
}
