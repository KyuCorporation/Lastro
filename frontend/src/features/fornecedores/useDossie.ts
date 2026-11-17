import { useQuery } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { Dossie } from "../../api/types";

/** GET /fornecedores/{cnpj}/dossie. Escopo de UFs e sócios decididos pelo backend. */
export function useDossie(cnpj: string | undefined) {
  const api = useApi();
  return useQuery<Dossie, ErroApi>({
    queryKey: ["dossie", cnpj],
    queryFn: () => api.fornecedores.dossie(cnpj!),
    enabled: Boolean(cnpj),
    retry: false,
  });
}
