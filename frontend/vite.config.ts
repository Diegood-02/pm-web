/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  // loadEnv incluye las variables VITE_* del entorno del shell (p. ej. en GitHub Actions).
  const env = loadEnv(mode, ".", "VITE_");
  return {
    base: env.VITE_BASE_PATH || "/",
    plugins: [react()],
    server: {
      host: "0.0.0.0",
      port: 5173,
    },
    test: {
      environment: "jsdom",
      globals: true,
      setupFiles: ["./tests/setup.ts"],
    },
  };
});
