import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { CarteiraCriada, CarteiraEntrada, CarteiraListada, Fila } from "../../api/types";

export function useCarteiras() {
  const api = useApi();
  return useQuery<CarteiraListada[], ErroApi>({ queryKey: ["carteiras"], queryFn: () => api.carteiras.listar() });
}

export function useCriarCarteira() {
  const api = useApi();
  const cliente = useQueryClient();
  return useMutation<CarteiraCriada, ErroApi, CarteiraEntrada>({
    mutationFn: (entrada) => api.carteiras.criar(entrada),
    onSuccess: () => cliente.invalidateQueries({ queryKey: ["carteiras"] }),
  });
}

export function useFila(id: string | undefined) {
  const api = useApi();
  return useQuery<Fila, ErroApi>({
    queryKey: ["fila", id],
    queryFn: () => api.carteiras.fila(id!),
    enabled: Boolean(id),
    retry: false,
  });
}

/** Colagem livre: um CNPJ por linha, ou separados por vírgula, ponto e vírgula ou espaço. */
export function separarCnpjs(texto: string): string[] {
  return texto
    .split(/[\s,;]+/)
    .map((c) => c.trim())
    .filter(Boolean);
}
