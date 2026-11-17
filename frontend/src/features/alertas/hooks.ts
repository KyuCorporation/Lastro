import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { Alerta, StatusAlerta } from "../../api/types";

/** Alertas do tenant. Recarrega ao voltar à tela: abrir uma fila pode ter gerado alertas novos. */
export function useAlertas(status?: StatusAlerta) {
  const api = useApi();
  return useQuery<Alerta[], ErroApi>({ queryKey: ["alertas", status ?? "todos"], queryFn: () => api.alertas.listar(status) });
}
