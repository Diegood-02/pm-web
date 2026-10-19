# Motor de programación (CPM)

Ubicación: `backend/app/scheduling/`. Son funciones puras y modelos inmutables, sin dependencias de base de datos ni de FastAPI.

## Modelos

- **Task**: `id`, `name`, `duration_days` (días laborables), `wbs`, `is_milestone`. Un hito debe tener duración 0.
- **Dependency**: `predecessor_id`, `successor_id`, `type` (FS, SS, FF, SF) y `lag_days`. El retraso puede ser negativo.
- **Calendar**: `working_weekdays` (por defecto lunes a viernes), `holidays`, `extra_working_days` y `hours_per_day`.

## Supuestos

1. **Unidad de duración: días laborables.** Una tarea de 5 días ocupa 5 días laborables del calendario, no 5 días corridos. `hours_per_day` no interviene en el cálculo de fechas; se usará para costos en la Fase 4.
2. **Inicio del proyecto.** El desplazamiento 0 es el primer día laborable en o después de la fecha de inicio. Si el proyecto empieza en sábado, arranca el lunes.
3. **Fecha de fin de una tarea.** Es el último día laborable que ocupa. Un hito cae en el día laborable en que ocurre.
4. **Calendario.** Una fecha en `extra_working_days` es laborable aunque sea fin de semana o feriado. Si una fecha es feriado y no está en `extra_working_days`, no es laborable.
5. **Dependencias.** Las cuatro relaciones usan el retraso en días laborables:
   - FS: inicio sucesora ≥ fin predecesora + retraso.
   - SS: inicio sucesora ≥ inicio predecesora + retraso.
   - FF: fin sucesora ≥ fin predecesora + retraso.
   - SF: fin sucesora ≥ inicio predecesora + retraso.
6. **Inicio no negativo.** Ninguna tarea empieza antes del desplazamiento 0, aunque un retraso negativo lo pediría. Se corta en 0.
7. **Holgura total** = fin tardío − fin temprano. **Ruta crítica** = tareas con holgura total ≤ 0.
8. **Holgura libre** = cuánto puede retrasarse una tarea sin mover el inicio temprano de ninguna sucesora. Se acota por la holgura total.
9. **Ciclos.** Se detectan con orden topológico (Kahn). El error indica solo las tareas que forman el ciclo, no las que dependen de él.
10. **Orden determinista.** Las tareas se procesan por `id` y la ruta crítica se ordena por inicio temprano.

## Fuera de alcance por ahora

- Recursos con capacidad limitada (nivelación de recursos).
- Calendarios por tarea o por recurso; hoy el calendario es uno por proyecto.
- Fechas restringidas (no antes de / no después de).
