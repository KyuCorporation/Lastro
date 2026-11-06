import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

import { ApiProvider } from "./api/ApiProvider";
import type { Api } from "./api";
import { AuthProvider } from "./auth/AuthProvider";
import type { Sessao } from "./auth/sessao";

/** Árvore de provedores comum à aplicação e aos testes: muda só a `Api` e a `Sessao` injetadas. */
export function Provedores({ api, sessao, children }: { api: Api; sessao: Sessao; children: ReactNode }) {
  const [queryClient] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } }),
  );
  return (
    <QueryClientProvider client={queryClient}>
      <ApiProvider api={api}>
        <AuthProvider sessao={sessao}>{children}</AuthProvider>
      </ApiProvider>
    </QueryClientProvider>
  );
}
