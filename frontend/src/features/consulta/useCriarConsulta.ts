import { useMutation } from "@tanstack/react-query";

import { useApi } from "../../api/ApiProvider";
import type { ErroApi } from "../../api/http";
import type { ConsultaEntrada, ConsultaSaida } from "../../api/types";

/** POST /consultas. Sem retry: cada pergunta é auditada e conta no limite de 30 por minuto. */
export function useCriarConsulta() {
  const api = useApi();
  return useMutation<ConsultaSaida, ErroApi, ConsultaEntrada>({
    mutationFn: (entrada) => api.consultas.criar(entrada),
    retry: false,
  });
}
