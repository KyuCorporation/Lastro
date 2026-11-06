// A API responde a negação de escopo com 403 ESCOPO_NEGADO (contracts/api.md), depois de gravar a consulta como
// "negada" e o evento na auditoria. Na tela, ela aparece no mesmo painel das outras respostas ("Acesso negado").

import { ErroApi } from "../../api/http";
import type { ConsultaSaida } from "../../api/types";

export function negacaoComoResultado(erro: unknown): ConsultaSaida | null {
  if (!(erro instanceof ErroApi) || erro.codigo !== "ESCOPO_NEGADO") return null;
  return {
    consulta_id: erro.requestId ?? "negada",
    status: "negada",
    resposta: erro.message,
    citacoes: [],
    recibo_id: null,
    sintetico: false,
  };
}
