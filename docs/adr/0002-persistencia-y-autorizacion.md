# ADR 0002: Persistencia, autenticación y autorización

- Estado: aceptado
- Fecha: 2026-10-19

## Contexto

La Fase 2 agrega la base de datos, la API REST y el control de acceso de un equipo multiusuario. Hay que decidir cómo se guardan los datos, cómo se autentican los usuarios y qué reglas de permisos aplican.

## Decisiones

- **ORM y migraciones:** SQLAlchemy 2.x con `Mapped[...]` y Alembic. Las restricciones tienen nombres estables (convención en `app/db.py`) para que las migraciones sean reproducibles. La migración inicial se generó con `alembic revision --autogenerate` y se revisó a mano.
- **Enumerados:** se guardan como texto con su valor (p. ej. `miembro`) y con restricción CHECK. No se usan tipos ENUM nativos de PostgreSQL, para que cambiar valores sea una migración simple.
- **Contraseñas:** hash con argon2 (`argon2-cffi`), recomendado por OWASP.
- **Tokens:** JWT firmados con HS256. Un token de acceso (30 min) y uno de refresco (7 días), distinguidos por el campo `type`. La clave viene solo de variables de entorno.
- **Alta de usuarios:** solo un admin crea usuarios (`POST /api/v1/users`). Es la forma de invitación. El primer admin se crea con `python -m app.cli create-admin`, que pide la contraseña por consola.
- **Roles:**
  - Global (`User.role`): `admin` administra usuarios y ve todos los proyectos; `project_manager` puede crear proyectos; `miembro` y `lector` no crean proyectos.
  - Por proyecto (`ProjectMember.role`): `project_manager` administra el proyecto, la línea base y el equipo; `miembro` edita tareas, dependencias, recursos y asignaciones; `lector` solo lee.
- **Visibilidad:** un no miembro recibe **404**, igual que si el proyecto no existiera. Así no se revela que existe.
- **Concurrencia:** las tareas y los proyectos tienen un campo `version`. Una edición con versión vieja responde **409** y no sobrescribe en silencio.
- **WBS:** el código (1, 1.2, ...) se calcula desde el árbol y no se guarda, para evitar que se desincronice.
- **Línea base:** copia de fechas en desplazamientos de días laborables. Las tareas borradas dejan su copia intacta (`task_id` pasa a nulo). La comparación reporta variaciones en días laborables.
- **Auditoría:** cada cambio escribe una fila en `audit_logs` dentro de la misma transacción.

## Consecuencias

- Los tokens no se pueden revocar antes de expirar. Si hace falta, se agregará una lista de revocación en la Fase 6.
- Los permisos viven en `app/deps.py`. Cualquier endpoint nuevo debe declarar su nivel de acceso con `ProjectReader`, `ProjectWriter` o `ProjectManager`.
- Las pruebas de integración usan PostgreSQL real (`pm_web_test`), no SQLite, para que las restricciones y los tipos se comporten igual que en producción.
