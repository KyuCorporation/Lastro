// Adaptador SIMULADO de POST /consultas, só para desenvolver a tela antes da orquestração (T11).
// Ligado por VITE_CONSULTAS_SIMULADAS=true. Toda resposta sai com `sintetico: true`, a tela mostra o aviso
// e os dados são fictícios (fonte demo_sintetico, CNPJ 99.999.999/0001-91). Não use na demo final.

import type { ApiConsultas } from "../index";
import type { ConsultaEntrada, ConsultaSaida } from "../types";

const COLETADO_EM = "2026-11-06T09:00:00Z";

function respondida(): Omit<ConsultaSaida, "consulta_id"> {
  return {
    status: "respondida",
    resposta:
      "A Empresa Exemplo (CNPJ 99.999.999/0001-91) tem 2 contratos vigentes em PE, que somam R$ 1.250.000,00 [1]. " +
      "O maior termina em 14/01/2027 e representa 80% do valor vigente [2].",
    citacoes: [
      {
        n: 1,
        tabela: "contratos",
        id: "00000000-0000-0000-0000-00000000c001",
        fonte_id: "demo_sintetico",
        url_origem: null,
        coletado_em: COLETADO_EM,
      },
      {
        n: 2,
        tabela: "contratos",
        id: "00000000-0000-0000-0000-00000000c002",
        fonte_id: "demo_sintetico",
        url_origem: null,
        coletado_em: COLETADO_EM,
      },
    ],
    recibo_id: null,
    sintetico: true,
  };
}

function negada(): Omit<ConsultaSaida, "consulta_id"> {
  return {
    status: "negada",
    resposta: "Você não tem acesso a dados de AL.",
    citacoes: [],
    recibo_id: null,
    sintetico: true,
  };
}

/** Respostas fixas para ensaiar os estados da tela. "Alagoas" ou " AL" na pergunta simula uma negação. */
export function consultasSimuladas(atrasoMs = 400): ApiConsultas {
  let contador = 0;
  return {
    async criar(entrada: ConsultaEntrada): Promise<ConsultaSaida> {
      await new Promise((resolver) => setTimeout(resolver, atrasoMs));
      contador += 1;
      const consulta_id = `simulada-${contador}`;
      const pedeOutraUf = /alagoas/i.test(entrada.pergunta) || /\bAL\b/.test(entrada.pergunta);
      return { consulta_id, ...(pedeOutraUf ? negada() : respondida()) };
    },
  };
}
