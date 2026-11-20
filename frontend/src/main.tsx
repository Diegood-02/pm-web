import { StrictMode } from "react";
import type { ComponentType, ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, HashRouter } from "react-router-dom";

import { API_BASE } from "./api/client";
import { App } from "./App";
import { AuthProvider } from "./auth/AuthContext";
import "./styles.css";

const Router: ComponentType<{ children: ReactNode }> =
  import.meta.env.VITE_ROUTER_MODE === "hash" ? HashRouter : BrowserRouter;

async function start(): Promise<void> {
  const container = document.getElementById("root");
  if (!container) {
    throw new Error("No se encontró el elemento #root");
  }
  if (import.meta.env.VITE_DEMO === "true") {
    // Solo se carga en el build de demo; el backend real no lo necesita.
    const { installDemoApi } = await import("./demo/demoApi");
    installDemoApi(API_BASE);
  }
  createRoot(container).render(
    <StrictMode>
      <Router>
        <AuthProvider>
          <App />
        </AuthProvider>
      </Router>
    </StrictMode>,
  );
}

void start();
