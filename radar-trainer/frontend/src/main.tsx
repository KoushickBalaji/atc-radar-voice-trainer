import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import TrainingEntry from "./TrainingEntry";
import { ThemeInit } from "../.flowbite-react/init";
import "./index.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ThemeInit />
    {location.search.includes('advanced=1') ? <App /> : <TrainingEntry />}
  </StrictMode>,
);
