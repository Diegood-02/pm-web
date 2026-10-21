# Checklist del piloto

Objetivo: que el equipo use PM Web en un proyecto real durante dos semanas y registre lo que funciona y lo que no.

## 1. Preparación (la hace quien opera)

- [ ] `.env` con todos los secretos cambiados (ver `docs/RUNBOOK.md`).
- [ ] `docker compose up -d --build` sin errores; `GET /api/v1/health/ready` responde `ready`.
- [ ] `make migrate` aplicado.
- [ ] Primer administrador creado con `create-admin`.
- [ ] Usuarios del equipo dados de alta con su rol global (`project_manager`, `miembro` o `lector`).
- [ ] Respaldo de la base programado y restauración probada en otra base.
- [ ] `WEB_BIND` y `API_BIND` ajustados según la red del piloto.

## 2. Proyecto de prueba (una tarde)

- [ ] Crear un proyecto nuevo y definir fecha de inicio y calendario (días laborables, feriados).
- [ ] Cargar 10 a 15 tareas reales con WBS: subtareas, reordenar, mover y eliminar.
- [ ] Crear dependencias de los cuatro tipos (FS, SS, FF, SF) y al menos un retraso negativo.
- [ ] Revisar la ruta crítica en el Gantt y en la tabla de cronograma.
- [ ] Crear recursos con tarifa por hora y asignarlos a tareas.
- [ ] Guardar una línea base y comparar después de mover una tarea.
- [ ] Registrar avance y costo real; revisar CPI, SPI y la alerta bajo 0.9.
- [ ] Exportar CSV, XLSX, PDF y JSON. Abrir cada archivo en su programa.
- [ ] Importar el JSON como copia y comparar cronograma y costos.
- [ ] Probar el proyecto de ejemplo (`seed-demo`) para ver una carga de 40 tareas.

## 3. Uso real (dos semanas)

- [ ] El proyecto real se carga en PM Web desde el inicio o se importa desde el JSON de otra herramienta.
- [ ] Al menos dos personas editan el mismo proyecto el mismo día. Anotar si el aviso de conflicto aparece y si es claro.
- [ ] Una semana de actualizaciones de avance y costo real por la persona que corresponde.
- [ ] Un reporte PDF enviado al cliente o a la dirección (solo si el piloto lo permite).

## 4. Criterios de salida

- [ ] El cronograma del proyecto real es igual al del plan de referencia, o las diferencias están explicadas.
- [ ] Ningún error 500 sin resolver. Todos los errores registrados tienen su `request_id`.
- [ ] Los indicadores de costo coinciden con la hoja de cálculo que el equipo usa hoy, con una diferencia aceptable.
- [ ] El tiempo de carga de la vista del proyecto es razonable para el equipo (anotar la cifra).

## 5. Registro de hallazgos

Llena la tabla durante el piloto. Prioridad: **A** bloquea el trabajo; **B** duele pero hay alternativa; **C** mejora.

| Fecha | Quién | Pantalla o endpoint | Qué pasó | Qué se esperaba | Prioridad | Estado |
|---|---|---|---|---|---|---|
| | | | | | | |

## 6. Cierre

- [ ] Reunión de cierre con el equipo: qué mantener, qué cambiar, qué falta para usarlo en serio.
- [ ] Hallazgos A y B resueltos o con fecha en el plan.
- [ ] Decisión: continuar, ajustar o detener el piloto.
