# ADR 0003: Frontend, sesión y actualización de datos

- Estado: aceptado
- Fecha: 2026-10-19

## Contexto

La Fase 3 entrega la interfaz del MVP: login, gestión de usuarios, proyectos con tres vistas de trabajo (tareas, Gantt, recursos) y la línea base. Debe actualizarse casi en tiempo real y no sobrescribir cambios de otras personas en silencio.

## Decisiones

- **Stack:** React 18 con TypeScript y Vite. Enrutamiento con `react-router-dom` 7 y Gantt con `frappe-gantt` 1.2.2. Ambas con versión exacta y publicadas hace más de dos semanas.
- **Sin gestor de estado global:** cada página carga sus datos con `useProjectData`, que trae en paralelo proyecto, miembros, tareas, dependencias, cronograma, recursos y asignaciones.
- **Actualización casi en tiempo real:** la vista se vuelve a cargar cada 15 segundos mientras la pestaña esté visible, y después de cada cambio propio. No se usan WebSockets; es suficiente para un equipo pequeño y evita infraestructura extra.
- **Control de concurrencia:** cada edición envía la `version` que el usuario tenía. Si la API responde 409, la interfaz muestra un aviso, recarga los datos y no guarda nada en silencio.
- **Tokens:** se guardan en `sessionStorage`, así que viven solo en la pestaña y se borran al cerrarla. El refresco se hace una vez cuando la API responde 401. No se usa `localStorage` para no dejar sesiones abiertas en equipos compartidos.
- **Permisos en la interfaz:** la interfaz oculta acciones según el rol del proyecto (lector, miembro, project manager), pero la API es la que decide. Ocultar un botón no es un control de seguridad.
- **Gantt:** `frappe-gantt` solo dibuja dependencias de fin a inicio. El resto de tipos (SS, FF, SF) se muestran en la tabla de dependencias, que es la fuente exacta. El diagrama declara esta limitación en pantalla.
- **Accesibilidad:** las pestañas siguen el patrón WAI-ARIA con flechas, Inicio y Fin. Todos los campos tienen etiqueta, los errores usan `role="alert"` y el contraste de los colores supera 4.5:1.
- **Tipos de frappe-gantt:** la librería no trae tipos. Se declaran solo los que se usan en `src/types/frappe-gantt.d.ts`.

## Consecuencias

- El intervalo de 15 segundos genera tráfico constante con muchas personas en el mismo proyecto. Si crece el número de usuarios, conviene pasar a eventos por WebSocket o SSE.
- El CSS de frappe-gantt se importa por ruta dentro de `node_modules`, porque su campo `exports` no expone esa subruta.
- Las vulnerabilidades reportadas por `npm audit` están en herramientas de desarrollo (Vitest, Vite, ESLint). Las dependencias de producción no tienen ninguna. Corregirlas requiere versiones mayores y queda como tarea aparte.
