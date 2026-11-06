import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { Recibo } from "../../api/types";

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
