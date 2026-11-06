// Cliente HTTP único. Põe o token, interpreta o formato de erro do contrato e avisa quando a sessão caiu.

import type { CodigoErro, CorpoErro } from "./types";

export class ErroApi extends Error {
  constructor(
    readonly status: number,
    readonly codigo: CodigoErro | string,
    mensagem: string,
    readonly requestId: string | null = null,
  ) {
    super(mensagem);
    this.name = "ErroApi";
  }
}

/** Mensagem usada quando a API não manda uma (rede fora, resposta sem corpo). */
const MENSAGENS_PADRAO: Record<string, string> = {
  NAO_AUTENTICADO: "Sua sessão expirou. Entre novamente.",
  PERFIL_SEM_PERMISSAO: "Seu perfil não tem permissão para esta ação.",
  ESCOPO_NEGADO: "Você não tem acesso a esses dados.",
  NAO_ENCONTRADO: "Não encontrado.",
  ENTRADA_INVALIDA: "Confira os dados informados.",
  LIMITE_EXCEDIDO: "Muitas consultas em pouco tempo. Aguarde um minuto.",
  FONTE_INDISPONIVEL: "Uma fonte de dados está indisponível no momento.",
  ERRO_INTERNO: "Erro inesperado. Tente de novo.",
  SEM_CONEXAO: "Não foi possível falar com o servidor. Verifique a conexão.",
};

export function mensagemPadrao(codigo: string): string {
  return MENSAGENS_PADRAO[codigo] ?? MENSAGENS_PADRAO.ERRO_INTERNO;
}

function ehCorpoErro(corpo: unknown): corpo is CorpoErro {
  return (
    typeof corpo === "object" &&
    corpo !== null &&
    "erro" in corpo &&
    typeof (corpo as CorpoErro).erro?.codigo === "string"
  );
}

export interface OpcoesHttp {
  baseUrl: string;
  /** Lê o token atual a cada requisição (pode mudar depois do login). */
  token: () => string | null;
  /** Chamado em qualquer 401: a camada de sessão faz logout. */
  aoPerderSessao?: () => void;
  fetch?: typeof fetch;
}

export interface Http {
  get<T>(caminho: string): Promise<T>;
  post<T>(caminho: string, corpo: unknown): Promise<T>;
}

export function criarHttp(opcoes: OpcoesHttp): Http {
  const executarFetch = opcoes.fetch ?? ((...args: Parameters<typeof fetch>) => fetch(...args));

  async function requisitar<T>(metodo: "GET" | "POST", caminho: string, corpo?: unknown): Promise<T> {
    const cabecalhos: Record<string, string> = { Accept: "application/json" };
    const token = opcoes.token();
    if (token) cabecalhos.Authorization = `Bearer ${token}`;
    if (corpo !== undefined) cabecalhos["Content-Type"] = "application/json";

    let resposta: Response;
    try {
      resposta = await executarFetch(`${opcoes.baseUrl}${caminho}`, {
        method: metodo,
        headers: cabecalhos,
        body: corpo === undefined ? undefined : JSON.stringify(corpo),
      });
    } catch {
      throw new ErroApi(0, "SEM_CONEXAO", mensagemPadrao("SEM_CONEXAO"));
    }

    const texto = await resposta.text();
    const dados: unknown = texto ? safeJson(texto) : null;

    if (!resposta.ok) {
      // 401 com token = sessão caiu. Sem token (ex.: senha errada no login) é só um erro da tela.
      if (resposta.status === 401 && token) opcoes.aoPerderSessao?.();
      if (ehCorpoErro(dados)) {
        const { codigo, mensagem, request_id } = dados.erro;
        throw new ErroApi(resposta.status, codigo, mensagem || mensagemPadrao(codigo), request_id);
      }
      const codigo = resposta.status === 401 ? "NAO_AUTENTICADO" : "ERRO_INTERNO";
      throw new ErroApi(resposta.status, codigo, mensagemPadrao(codigo), resposta.headers.get("X-Request-ID"));
    }
    return dados as T;
  }

  return {
    get: (caminho) => requisitar("GET", caminho),
    post: (caminho, corpo) => requisitar("POST", caminho, corpo),
  };
}

function safeJson(texto: string): unknown {
  try {
    return JSON.parse(texto);
  } catch {
    return null;
  }
}
