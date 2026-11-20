// Banderas del modo demo. Este módulo es pequeño y no carga el snapshot de datos.

export const DEMO_ENABLED = import.meta.env.VITE_DEMO === "true";
export const DEMO_READONLY_MESSAGE =
  "La demo es de solo lectura: los cambios no se guardan. Para editar, usa la instalación del piloto.";
