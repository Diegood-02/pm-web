# ADR 0004: Costos y valor ganado (EVM)

- Estado: aceptado
- Fecha: 2026-10-19

## Contexto

La Fase 4 agrega costos por recurso, costos fijos por tarea y los indicadores de valor ganado: PV, EV, AC, CV, SV, CPI y SPI, con alerta visual cuando CPI o SPI bajan de 0.9.

## Decisiones

- **Tarifa por recurso:** `Resource.hourly_rate`. El costo de mano de obra de una asignación es `tarifa × (unidades / 100) × horas por día × duración en días`.
- **Costo fijo por tarea:** `Task.fixed_cost`. Un hito puede tener costo fijo, aunque no tiene mano de obra.
- **Presupuesto de tarea (BAC):** suma de la mano de obra de sus asignaciones más el costo fijo.
- **Avance real:** `Task.percent_complete` (0 a 100), capturado manualmente. EV = presupuesto × avance.
- **Costo real:** `Task.actual_cost`, capturado manualmente por tarea. El sistema no se conecta a contabilidad; esa integración queda fuera de alcance.
- **Valor planeado (PV):** avance lineal del presupuesto sobre los días laborables de la tarea hasta la fecha de corte. Un hito vale todo su presupuesto al llegar a su fecha. Usa el mismo calendario del proyecto que el cronograma.
- **Índices:** CPI = EV / AC y SPI = EV / PV, con 4 decimales. Si el denominador es cero, el índice no se calcula (`null`) y no dispara alerta.
- **Umbral de alerta:** 0.9, constante en `app/costing/evm.py`. Un índice menor dispara `cpi_alert` o `spi_alert`.
- **Línea base con costos:** cada tarea guarda su presupuesto al crear la línea base. Así se cumple lo que pedía la Fase 2 y que faltaba en esa entrega.
- **Moneda:** los montos no llevan moneda en la API. La interfaz los muestra en MXN porque la zona horaria por defecto es America/Mexico_City. Si el proyecto necesita otra moneda, habrá que agregar un campo al proyecto.
- **Permisos:** cualquier miembro del proyecto, incluido el lector, puede ver el reporte de costos. Editar avance, costo real o tarifas requiere ser miembro o project manager. Si la empresa quiere ocultar costos a los lectores, es un cambio pequeño en `app/routers/costs.py`.
- **Precisión:** los montos se guardan como `Numeric` en la base y se calculan como `Decimal`. En JSON se envían como número con dos decimales, lo que es suficiente para esta etapa.

## Consecuencias

- El valor planeado se calcula a la fecha de corte que pida el usuario. No hay historial de PV por fecha; si se necesita una curva S, habrá que guardar snapshots.
- El costo real y el avance se capturan a mano. Si el equipo necesita registrar horas reales, habrá que agregar registros de tiempo por tarea y recurso.
