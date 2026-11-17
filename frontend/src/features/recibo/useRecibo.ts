import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { Recibo, VerificacaoRecibo } from "../../api/types";

/** GET /recibos/{id}. O recibo é imutável: pode ficar em cache. */
export function useRecibo(id: string | null | undefined) {
  const api = useApi();
  return useQuery<Recibo, ErroApi>({
    queryKey: ["recibo", id],
    queryFn: () => api.recibos.obter(id!),
    enabled: Boolean(id),
    staleTime: Infinity,
    retry: false,
  });
}

/** GET /recibos/{id}/verificar: o servidor recalcula o hash a cada abertura (sem cache). */
export function useVerificacaoRecibo(id: string | null | undefined) {
  const api = useApi();
  return useQuery<VerificacaoRecibo, ErroApi>({
    queryKey: ["recibo-verificacao", id],
    queryFn: () => api.recibos.verificar(id!),
    enabled: Boolean(id),
    staleTime: 0,
    retry: false,
  });
}
