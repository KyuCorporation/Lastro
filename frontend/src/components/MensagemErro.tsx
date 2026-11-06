import { ErroApi, mensagemPadrao } from "../api/http";

/** Erro sempre em texto (nunca só cor), com o request_id para quem for investigar no log. */
export function MensagemErro({ erro, titulo = "Não foi possível concluir" }: { erro: unknown; titulo?: string }) {
  const mensagem = erro instanceof ErroApi ? erro.message : mensagemPadrao("ERRO_INTERNO");
  const requestId = erro instanceof ErroApi ? erro.requestId : null;
  return (
    <div role="alert" className="rounded-md border border-red-700 bg-red-50 p-4 text-red-900">
      <p className="font-semibold">{titulo}</p>
      <p>{mensagem}</p>
      {requestId && <p className="mt-1 text-sm text-red-800">Código do pedido: {requestId}</p>}
    </div>
  );
}
