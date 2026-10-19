"""Errores del motor de programación."""


class SchedulingError(ValueError):
    """Datos de entrada inválidos para el motor de programación."""


class CyclicDependencyError(SchedulingError):
    """Las dependencias forman un ciclo; no existe un orden de ejecución válido."""

    def __init__(self, task_ids: list[int]) -> None:
        self.task_ids = task_ids
        ids = ", ".join(str(task_id) for task_id in task_ids)
        super().__init__(f"Ciclo detectado en las dependencias de las tareas: {ids}")
