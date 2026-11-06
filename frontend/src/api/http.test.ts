import { consultasSimuladas } from "./adaptadores/consultasSimuladas";
import { ErroApi, criarHttp } from "./http";

function resposta(status: number, corpo?: unknown) {
  return new Response(corpo === undefined ? null : JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("criarHttp", () => {
  it("envia o token e o corpo em JSON", async () => {
    const fetchFalso = vi.fn(async () => resposta(200, { ok: true }));
    const http = criarHttp({ baseUrl: "http://api.test", token: () => "abc", fetch: fetchFalso });
    await http.post("/consultas", { pergunta: "oi" });
    const [url, init] = fetchFalso.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("http://api.test/consultas");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer abc");
    expect(init.body).toBe(JSON.stringify({ pergunta: "oi" }));
  });

  it("transforma o erro do contrato em ErroApi", async () => {
    const corpo = { erro: { codigo: "ESCOPO_NEGADO", mensagem: "Você não tem acesso a dados de AL.", request_id: "r1" } };
    const http = criarHttp({ baseUrl: "", token: () => "abc", fetch: async () => resposta(403, corpo) });
    const erro = await http.get("/x").catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroApi);
    expect(erro).toMatchObject({ status: 403, codigo: "ESCOPO_NEGADO", requestId: "r1" });
    expect((erro as ErroApi).message).toBe("Você não tem acesso a dados de AL.");
  });

  it("401 com token avisa a sessão; 401 sem token (login errado) não", async () => {
    const aoPerderSessao = vi.fn();
    const corpo = { erro: { codigo: "NAO_AUTENTICADO", mensagem: "x", request_id: "r" } };
    let token: string | null = "abc";
    const http = criarHttp({ baseUrl: "", token: () => token, aoPerderSessao, fetch: async () => resposta(401, corpo) });
    await http.get("/me").catch(() => undefined);
    token = null;
    await http.post("/auth/login", {}).catch(() => undefined);
    expect(aoPerderSessao).toHaveBeenCalledTimes(1);
  });

  it("falha de rede vira SEM_CONEXAO", async () => {
    const http = criarHttp({
      baseUrl: "",
      token: () => null,
      fetch: async () => {
        throw new TypeError("offline");
      },
    });
    await expect(http.get("/x")).rejects.toMatchObject({ codigo: "SEM_CONEXAO", status: 0 });
  });

  it("erro sem corpo usa mensagem padrão em português", async () => {
    const http = criarHttp({ baseUrl: "", token: () => null, fetch: async () => resposta(500) });
    await expect(http.get("/x")).rejects.toMatchObject({ codigo: "ERRO_INTERNO", message: "Erro inesperado. Tente de novo." });
  });
});

describe("consultasSimuladas", () => {
  it("sempre marca a resposta como sintética", async () => {
    const api = consultasSimuladas(0);
    const r1 = await api.criar({ pergunta: "Contratos do CNPJ 99.999.999/0001-91" });
    const r2 = await api.criar({ pergunta: "Quanto recebeu em Alagoas?" });
    expect([r1.sintetico, r2.sintetico]).toEqual([true, true]);
    expect([r1.status, r2.status]).toEqual(["respondida", "negada"]);
    expect(r1.consulta_id).not.toBe(r2.consulta_id);
  });
});
