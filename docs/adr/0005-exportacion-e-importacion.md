# ADR 0005: Exportación e importación de proyectos

- Estado: aceptado
- Fecha: 2026-10-19

## Contexto

La Fase 5 pide exportar el cronograma a CSV y XLSX, un reporte PDF de resumen, y un formato propio en JSON con validación de esquema que permita respaldar y mover proyectos.

## Decisiones

- **CSV:** UTF-8 con BOM para que Excel abra los acentos correctamente. Encabezados en español, una fila por tarea en orden WBS.
- **XLSX:** hoja "Cronograma" con encabezados en negrita, fechas como fecha real y las tareas críticas resaltadas. Hoja "Proyecto" con totales.
- **PDF:** resumen con fechas, ruta crítica, valor ganado (si hay tarifas o costos), y la tabla del cronograma. Se genera con ReportLab, sin fuentes externas.
- **JSON (formato `pm-web-project`, versión 1):** esquema JSON Draft 2020-12 en `app/exports/project_v1.schema.json`. Es estricto: no se aceptan campos desconocidos. Límites: 5 000 tareas, 500 recursos, 20 000 dependencias y 20 000 asignaciones.
- **Referencias locales:** el documento usa `T1`, `R1`, etc. en lugar de ids de base de datos, así que puede importarse en otra instancia. El orden de las tareas entre hermanas se conserva.
- **Validación en dos niveles:** primero el esquema; después reglas que el esquema no expresa: referencias existentes, refs sin repetir, hitos con duración 0, zona horaria válida, jerarquía sin ciclos, dependencias sin ciclos, y sin asignaciones ni dependencias repetidas. Un error devuelve 422 con la lista completa de problemas.
- **Importar siempre crea un proyecto nuevo.** No fusiona con uno existente. Quien importa queda como project manager.
- **Permisos:** descargar requiere ser lector o superior, igual que ver el proyecto. Importar requiere rol global admin o project_manager, igual que crear un proyecto.
- **Qué no se exporta:** líneas base y comentarios. Las líneas base son fotografías de un momento y se pueden recrear; los comentarios quedan para cuando existan endpoints.

## Consecuencias

- El tamaño del cuerpo de la petición de importación no tiene límite explícito todavía; los límites de tamaño llegan en la Fase 6.
- Si cambia el formato, se crea `project_v2.schema.json` y la importación acepta ambas versiones. La versión 1 no se modifica.
- Las fechas del PDF y del CSV dependen de la fecha de corte; el PDF usa hoy por defecto.
