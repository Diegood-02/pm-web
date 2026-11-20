# Runbook de operación

Para quien opera la instalación del piloto. Supone Docker Compose y el archivo `.env` configurado.

## Antes de arrancar

1. Copia `.env.example` a `.env`.
2. Cambia **todos** los valores `cambia-...`. Son obligatorios: sin `POSTGRES_PASSWORD`, `DATABASE_URL` o `JWT_SECRET_KEY` (32 caracteres o más) los servicios no arrancan.
3. Genera la clave JWT con: `python -c "import secrets; print(secrets.token_urlsafe(48))"`.
4. Si el piloto es en la red de la oficina, pon `API_BIND=0.0.0.0` y `WEB_BIND=0.0.0.0` en `.env`. Por defecto solo se escucha en `127.0.0.1`.
5. Si `CORS_ALLOWED_ORIGINS` cambia, actualiza también `VITE_API_URL` para que la web apunte a la API correcta.

## Arranque y parada

```bash
docker compose up -d --build     # levanta db, api y web
docker compose ps                # estado de cada servicio
docker compose down              # detiene los servicios (conserva los datos)
```

Comprobaciones:

- `GET /api/v1/health`: el proceso de la API responde.
- `GET /api/v1/health/ready`: la API tiene conexión a la base. Devuelve 503 si la base no responde.

## Migraciones de base de datos

Corre las migraciones después de cada actualización del código:

```bash
make migrate        # equivale a: docker compose exec api alembic upgrade head
```

## Usuarios y datos de ejemplo

```bash
# Primer administrador (pide la contraseña por consola)
docker compose exec -it api python -m app.cli create-admin --email tu@correo.com --name "Tu nombre"

# Proyecto de ejemplo de 40 tareas, a nombre de un project manager ya existente
docker compose exec api python -m app.cli seed-demo --email pm@correo.com
```

Los demás usuarios los da de alta un admin desde la pantalla **Usuarios** o con `POST /api/v1/users`.

## Respaldo y restauración

Respalda la base cada día, como mínimo:

```bash
docker compose exec -T db pg_dump -U pm -Fc pm_web > respaldo-$(date +%F).dump
```

Restaura solo en una base vacía o de pruebas (esto sobrescribe datos):

```bash
docker compose exec -T db pg_restore -U pm -d pm_web --clean --if-exists < respaldo-AAAA-MM-DD.dump
```

Guarda los respaldos fuera del equipo. Un respaldo que nunca se ha restaurado no sirve: prueba la restauración en otra base una vez antes del piloto.

## Logs

Los logs de la API salen en JSON, una línea por evento:

```bash
docker compose logs -f api
docker compose logs api --since 1h | grep '"level": "ERROR"'
```

Cada petición tiene un `request_id`. Se devuelve en la cabecera `X-Request-ID` y aparece en los errores (`request_id`). Si un usuario reporta un problema, pídele ese valor y búscalo en los logs.

Los logs no contienen contraseñas, tokens, cabeceras ni cuerpos de petición.

## Problemas frecuentes

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `health/ready` responde 503 | La base no está arriba o la contraseña no coincide con `.env` | `docker compose ps`; revisa `POSTGRES_PASSWORD` y `DATABASE_URL` |
| 401 en todas las peticiones | El token expiró o la clave JWT cambió | Vuelve a iniciar sesión |
| 429 al iniciar sesión | Demasiados intentos fallidos desde esa IP para ese correo | Espera 15 minutos o reinicia la API (`docker compose restart api`) |
| 413 al importar | El archivo pasa de `MAX_REQUEST_BYTES` (2 MB por defecto) | Divide el proyecto o sube el límite con cuidado |
| 422 "límite de 5000 tareas" | El proyecto llegó al tope por proyecto | Usa varios proyectos o sube `MAX_TASKS_PER_PROJECT` |
| La web no carga datos | `VITE_API_URL` no coincide con la URL real de la API | Corrige `.env` y ejecuta `docker compose up -d --build web` |
| Error 500 | Error no controlado | Busca el `request_id` del mensaje en `docker compose logs api` |

## Rotar secretos

- **Clave JWT:** cámbiala en `.env` y reinicia la API. Las sesiones activas dejan de valer y los usuarios deben volver a entrar.
- **Contraseña de la base:** cámbiala en `.env`, en la base (`ALTER USER pm PASSWORD '...'`) y reinicia los servicios.
- **Contraseñas de usuarios:** un admin no puede verlas. Si alguien la olvida, el admin crea otro usuario o restablece la contraseña desde la base. Falta una pantalla de restablecimiento; ver `docs/SEGURIDAD.md`.

## Límites actuales

- Tamaño de petición: 2 MB (`MAX_REQUEST_BYTES`).
- Tareas por proyecto: 5 000 (`MAX_TASKS_PER_PROJECT`).
- Intentos de login: 5 fallidos cada 15 minutos por correo e IP (`LOGIN_MAX_FAILURES`, `LOGIN_WINDOW_MINUTES`). El contador vive en memoria: se reinicia al reiniciar la API.
- Un solo proceso de API. Escalar a varios requiere mover el contador de login a la base o a Redis.
