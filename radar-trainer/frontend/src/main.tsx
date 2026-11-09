import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import SimpleApp from "./SimpleApp";
import { ThemeInit } from "../.flowbite-react/init";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeInit />
    {location.search.includes('advanced=1') ? <App /> : <SimpleApp />}
  </StrictMode>,
);
