import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import { Provedores } from "./Provedores";
import { criarApi } from "./api";
import { criarHttp } from "./api/http";
import { criarSessao } from "./auth/sessao";
import { FUTURO_ROUTER, ambiente } from "./config/ambiente";
import "./index.css";

const sessao = criarSessao();
const http = criarHttp({
  baseUrl: ambiente.apiUrl,
  token: () => sessao.token.ler(),
  aoPerderSessao: () => sessao.perder(),
});
const api = criarApi(http, { consultasSimuladas: ambiente.consultasSimuladas });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter future={FUTURO_ROUTER}>
      <Provedores api={api} sessao={sessao}>
        <App />
      </Provedores>
    </BrowserRouter>
  </StrictMode>,
);
