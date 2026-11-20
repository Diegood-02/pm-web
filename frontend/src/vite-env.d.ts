/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  /** "true" activa el modo demo de solo lectura (GitHub Pages). */
  readonly VITE_DEMO?: string;
  /** "hash" usa rutas #/ (necesario en GitHub Pages); por defecto, rutas normales. */
  readonly VITE_ROUTER_MODE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
