import React from "react";
import ReactDOM from "react-dom/client";
// Fontes empacotadas (item 7): woff2 variáveis via fontsource, pré-carregadas
// no arranque — a app é offline, nada vem de CDN. O registo com metadados que
// a UI lê está em fonts.json; fonte nova = 1 pacote npm + 1 import + 1 linha lá.
import "@fontsource-variable/inter";
import "@fontsource-variable/geist";
import "@fontsource-variable/roboto-flex";
import "@fontsource-variable/open-sans";
import "@fontsource/lato";
import "@fontsource-variable/source-sans-3";
import "@fontsource-variable/ibm-plex-sans";
import "@fontsource-variable/manrope";
import "@fontsource-variable/dm-sans";
import "@fontsource-variable/figtree";
import "@fontsource-variable/nunito-sans";
import "@fontsource-variable/public-sans";
import "@fontsource-variable/lexend";
import "@fontsource/atkinson-hyperlegible";
import App from "./App";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
