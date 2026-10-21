# Revisión de seguridad básica (Fase 6)

Fecha: 2026-10-20. Alcance: backend, base de datos, contenedores y frontend, para el piloto interno. No es una auditoría externa.

## Resultados

| Área | Control | Estado |
|---|---|---|
| Entradas | Validación con Pydantic (tipos, rangos, longitudes) en todos los endpoints | Cumple |
| Entradas | Importación validada con JSON Schema y reglas de negocio; 422 con la lista completa de errores | Cumple |
| Inyección SQL | Consultas con SQLAlchemy (parámetros enlazados). No hay SQL construido con texto del usuario | Cumple |
| Secretos | `DATABASE_URL`, `JWT_SECRET_KEY` y `POSTGRES_PASSWORD` no tienen valor por defecto. Compose falla si faltan | Cumple |
| Secretos | `.env` está en `.gitignore`; solo se versiona `.env.example` con placeholders | Cumple |
| CORS | Orígenes desde `CORS_ALLOWED_ORIGINS`; métodos y cabeceras limitados | Cumple |
| Contraseñas | Hash con argon2; longitud mínima de 12 caracteres | Cumple |
| Sesiones | JWT HS256 con expiración (30 min de acceso, 7 días de refresco) y tipo de token verificado | Cumple con riesgo aceptado (ver abajo) |
| Fuerza bruta | 5 intentos fallidos por correo e IP cada 15 minutos → 429 | Cumple con límite (ver abajo) |
| Autorización | Un no miembro recibe 404; roles por proyecto en cada endpoint | Cumple |
| Errores | Errores no controlados responden 500 genérico con `request_id`; sin trazas al cliente | Cumple |
| Tamaño | 2 MB por petición (413), con o sin `Content-Length`; 5 000 tareas por proyecto | Cumple |
| Cabeceras | `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy`; `no-store` en autenticación | Cumple |
| Logs | JSON; sin contraseñas, tokens, cabeceras ni cuerpos | Cumple |
| Red | Base y servicios publicados solo en `127.0.0.1` por defecto | Cumple (configurable) |
| Contenedores | Imágenes `python:3.12-slim` y `node:24-alpine` | Revisar (ver abajo) |

## Riesgos aceptados para el piloto

1. **Los tokens no se revocan.** Si un token se filtra, vale hasta que expire (30 minutos para acceso). Mitigación: al rotar `JWT_SECRET_KEY` se invalidan todas las sesiones. Lista de revocación pendiente.
2. **Sin HTTPS dentro de la aplicación.** Si el piloto sale de la red de la oficina, pon un proxy con TLS delante (Caddy, nginx o similar). No envíes contraseñas por HTTP fuera de la red local.
3. **Contador de login en memoria.** Funciona con un solo proceso de API. Con varios procesos, el límite se multiplica.
4. **Sin cambio obligatorio de contraseña temporal.** Un admin define la contraseña inicial de cada usuario y no hay pantalla de restablecimiento. Pendiente.
5. **La documentación interactiva (`/docs`) está activa.** Expone la lista de endpoints, sin datos. Para producción conviene desactivarla.
6. **Vulnerabilidades en herramientas de desarrollo del frontend** (`npm audit`: Vitest, Vite, ESLint). No están en el bundle de producción, pero el servidor de desarrollo de Vite queda expuesto si `WEB_BIND` no es local. Pendiente de actualización mayor.

## Pendientes antes de producción

- Pantalla o comando de restablecimiento de contraseña y cambio obligatorio en el primer inicio de sesión.
- Revocación de tokens (lista o versión por usuario).
- Desactivar `/docs` y `/openapi.json` fuera de desarrollo.
- Escanear las imágenes de contenedor en CI.
- Roles separados en Postgres: uno para migraciones y otro para la aplicación.
