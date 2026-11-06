import { Navigate, Outlet, Route, Routes } from "react-router-dom";

import { RotaProtegida } from "./auth/RotaProtegida";
import { Cabecalho } from "./components/Cabecalho";
import { ConsultaPage } from "./pages/ConsultaPage";
import { LoginPage } from "./pages/LoginPage";
import { ReciboPage } from "./pages/ReciboPage";

function Layout() {
  return (
    <RotaProtegida>
      <a
        href="#conteudo"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:rounded focus:bg-white focus:p-2"
      >
        Pular para o conteúdo
      </a>
      <Cabecalho />
      <div id="conteudo">
        <Outlet />
      </div>
    </RotaProtegida>
  );
}

/** Rotas. Tela nova (T22, T26) = uma <Route> dentro do Layout e uma página em pages/. */
export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<Layout />}>
        <Route index element={<ConsultaPage />} />
        <Route path="/recibos/:id" element={<ReciboPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
