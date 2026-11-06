import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { useApi } from "../api/ApiProvider";
import type { LoginEntrada, Usuario } from "../api/types";
import type { Sessao } from "./sessao";

type EstadoAuth =
  | { status: "verificando" }
  | { status: "anonimo"; motivo?: "expirou" | "saiu" }
  | { status: "autenticado"; usuario: Usuario };

interface ValorAuth {
  estado: EstadoAuth;
  usuario: Usuario | null;
  entrar(entrada: LoginEntrada): Promise<Usuario>;
  sair(): void;
}

const AuthContext = createContext<ValorAuth | null>(null);

export function AuthProvider({ sessao, children }: { sessao: Sessao; children: ReactNode }) {
  const api = useApi();
  const queryClient = useQueryClient();
  const [estado, setEstado] = useState<EstadoAuth>(() =>
    sessao.token.ler() ? { status: "verificando" } : { status: "anonimo" },
  );

  // Token guardado de antes: confirma com /me. Quem diz quem é o usuário é o backend, não o storage.
  useEffect(() => {
    if (estado.status !== "verificando") return;
    let ativo = true;
    api.auth
      .me()
      .then((usuario) => ativo && setEstado({ status: "autenticado", usuario }))
      .catch(() => {
        sessao.token.apagar();
        if (ativo) setEstado({ status: "anonimo", motivo: "expirou" });
      });
    return () => {
      ativo = false;
    };
  }, [api, sessao, estado.status]);

  useEffect(
    () =>
      sessao.aoPerder(() => {
        queryClient.clear();
        setEstado({ status: "anonimo", motivo: "expirou" });
      }),
    [sessao, queryClient],
  );

  const entrar = useCallback(
    async (entrada: LoginEntrada) => {
      const { token, usuario } = await api.auth.login(entrada);
      sessao.token.gravar(token);
      setEstado({ status: "autenticado", usuario });
      return usuario;
    },
    [api, sessao],
  );

  const sair = useCallback(() => {
    sessao.token.apagar();
    queryClient.clear();
    setEstado({ status: "anonimo", motivo: "saiu" });
  }, [sessao, queryClient]);

  const valor = useMemo<ValorAuth>(
    () => ({ estado, usuario: estado.status === "autenticado" ? estado.usuario : null, entrar, sair }),
    [estado, entrar, sair],
  );

  return <AuthContext.Provider value={valor}>{children}</AuthContext.Provider>;
}

export function useAuth(): ValorAuth {
  const valor = useContext(AuthContext);
  if (!valor) throw new Error("useAuth fora do AuthProvider");
  return valor;
}
