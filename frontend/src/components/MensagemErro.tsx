import { ErroApi, mensagemPadrao } from "../api/http";

/** Erro sempre em texto (nunca só cor), com o request_id para quem for investigar no log. */
export function MensagemErro({ erro, titulo = "Não foi possível concluir" }: { erro: unknown; titulo?: string }) {
  const mensagem = erro instanceof ErroApi ? erro.message : mensagemPadrao("ERRO_INTERNO");
  const requestId = erro instanceof ErroApi ? erro.requestId : null;
  return (
    <div role="alert" className="rounded-md border border-kyu-vermelho bg-kyu-vermelho-fundo p-4 text-kyu-vermelho">
      <p className="font-semibold">{titulo}</p>
      <p>{mensagem}</p>
      {requestId && <p className="mt-1 text-sm">Código do pedido: {requestId}</p>}
    </div>
  );
}
