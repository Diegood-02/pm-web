"""Método de la ruta crítica (CPM).

Todos los cálculos se hacen en "desplazamientos": enteros de días laborables
contados desde el primer día laborable del proyecto (desplazamiento 0).
Las fechas reales se obtienen al final con el calendario.
"""

import heapq
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from itertools import islice

from app.scheduling.errors import CyclicDependencyError, SchedulingError
from app.scheduling.models import Calendar, Dependency, DependencyType, Task


@dataclass(frozen=True, slots=True)
class TaskSchedule:
    task_id: int
    early_start: int
    early_finish: int
    late_start: int
    late_finish: int
    total_float: int
    free_float: int
    is_critical: bool
    start_date: date
    finish_date: date


@dataclass(frozen=True, slots=True)
class Schedule:
    project_start: date
    project_finish: date
    duration_days: int
    tasks: dict[int, TaskSchedule]
    critical_path: tuple[int, ...]


def compute_schedule(
    tasks: Sequence[Task],
    dependencies: Sequence[Dependency],
    calendar: Calendar,
    project_start: date,
) -> Schedule:
    """Calcula fechas tempranas y tardías, holguras, ruta crítica y fechas reales."""
    task_by_id = _index_tasks(tasks)
    _validate_dependencies(task_by_id, dependencies)

    predecessors: dict[int, list[Dependency]] = defaultdict(list)
    successors: dict[int, list[Dependency]] = defaultdict(list)
    for dependency in dependencies:
        predecessors[dependency.successor_id].append(dependency)
        successors[dependency.predecessor_id].append(dependency)

    order = _topological_order(task_by_id, dependencies)

    early_start, early_finish = _forward_pass(order, task_by_id, predecessors)
    project_length = max(early_finish.values(), default=0)
    late_start, late_finish = _backward_pass(order, task_by_id, successors, project_length)

    working_days = list(islice(calendar.working_days_from(project_start), project_length + 1))

    schedules: dict[int, TaskSchedule] = {}
    for task_id in order:
        total_float = late_start[task_id] - early_start[task_id]
        free_float = _free_float(
            task_id,
            total_float,
            early_start,
            early_finish,
            successors,
            project_length,
        )
        schedules[task_id] = TaskSchedule(
            task_id=task_id,
            early_start=early_start[task_id],
            early_finish=early_finish[task_id],
            late_start=late_start[task_id],
            late_finish=late_finish[task_id],
            total_float=total_float,
            free_float=free_float,
            is_critical=total_float <= 0,
            start_date=working_days[early_start[task_id]],
            finish_date=_finish_date(early_start[task_id], early_finish[task_id], working_days),
        )

    critical_path = tuple(
        sorted(
            (s.task_id for s in schedules.values() if s.is_critical),
            key=lambda task_id: (early_start[task_id], task_id),
        )
    )

    return Schedule(
        project_start=working_days[0],
        project_finish=_finish_date(0, project_length, working_days),
        duration_days=project_length,
        tasks=schedules,
        critical_path=critical_path,
    )


def _index_tasks(tasks: Sequence[Task]) -> dict[int, Task]:
    task_by_id: dict[int, Task] = {}
    for task in tasks:
        if task.id in task_by_id:
            raise SchedulingError(f"El id de tarea {task.id} está repetido")
        task_by_id[task.id] = task
    return task_by_id


def _validate_dependencies(task_by_id: dict[int, Task], dependencies: Sequence[Dependency]) -> None:
    for dependency in dependencies:
        for task_id in (dependency.predecessor_id, dependency.successor_id):
            if task_id not in task_by_id:
                raise SchedulingError(f"La dependencia usa una tarea inexistente: {task_id}")


def _topological_order(
    task_by_id: dict[int, Task], dependencies: Sequence[Dependency]
) -> list[int]:
    """Orden topológico determinista (por id). Lanza error si hay ciclo."""
    indegree = dict.fromkeys(task_by_id, 0)
    outgoing: dict[int, list[int]] = defaultdict(list)
    for dependency in dependencies:
        outgoing[dependency.predecessor_id].append(dependency.successor_id)
        indegree[dependency.successor_id] += 1

    ready = [task_id for task_id, degree in indegree.items() if degree == 0]
    heapq.heapify(ready)
    order: list[int] = []
    while ready:
        task_id = heapq.heappop(ready)
        order.append(task_id)
        for successor_id in outgoing[task_id]:
            indegree[successor_id] -= 1
            if indegree[successor_id] == 0:
                heapq.heappush(ready, successor_id)

    if len(order) != len(task_by_id):
        remaining = {task_id for task_id, degree in indegree.items() if degree > 0}
        raise CyclicDependencyError(_cycle_members(remaining, dependencies))
    return order


def _cycle_members(remaining: set[int], dependencies: Sequence[Dependency]) -> list[int]:
    """Quita las tareas que solo dependen del ciclo y no forman parte de él."""
    outgoing: dict[int, set[int]] = {task_id: set() for task_id in remaining}
    for dependency in dependencies:
        if dependency.predecessor_id in remaining and dependency.successor_id in remaining:
            outgoing[dependency.predecessor_id].add(dependency.successor_id)

    members = set(remaining)
    changed = True
    while changed:
        changed = False
        for task_id in list(members):
            if not outgoing[task_id] & members:
                members.discard(task_id)
                changed = True
    return sorted(members)


def _forward_pass(
    order: list[int],
    task_by_id: dict[int, Task],
    predecessors: dict[int, list[Dependency]],
) -> tuple[dict[int, int], dict[int, int]]:
    early_start: dict[int, int] = {}
    early_finish: dict[int, int] = {}
    for task_id in order:
        duration = task_by_id[task_id].duration_days
        start = 0
        for dependency in predecessors[task_id]:
            pred_start = early_start[dependency.predecessor_id]
            pred_finish = early_finish[dependency.predecessor_id]
            lag = dependency.lag_days
            match dependency.type:
                case DependencyType.FS:
                    start = max(start, pred_finish + lag)
                case DependencyType.SS:
                    start = max(start, pred_start + lag)
                case DependencyType.FF:
                    start = max(start, pred_finish + lag - duration)
                case DependencyType.SF:
                    start = max(start, pred_start + lag - duration)
        early_start[task_id] = start
        early_finish[task_id] = start + duration
    return early_start, early_finish


def _backward_pass(
    order: list[int],
    task_by_id: dict[int, Task],
    successors: dict[int, list[Dependency]],
    project_length: int,
) -> tuple[dict[int, int], dict[int, int]]:
    late_start: dict[int, int] = {}
    late_finish: dict[int, int] = {}
    for task_id in reversed(order):
        duration = task_by_id[task_id].duration_days
        finish = project_length
        if successors[task_id]:
            finish = min(
                _latest_finish_limit(dependency, duration, late_start, late_finish)
                for dependency in successors[task_id]
            )
        late_finish[task_id] = finish
        late_start[task_id] = finish - duration
    return late_start, late_finish


def _latest_finish_limit(
    dependency: Dependency,
    predecessor_duration: int,
    late_start: dict[int, int],
    late_finish: dict[int, int],
) -> int:
    """Fecha de fin tardía máxima de la predecesora que respeta esta dependencia."""
    succ_start = late_start[dependency.successor_id]
    succ_finish = late_finish[dependency.successor_id]
    lag = dependency.lag_days
    match dependency.type:
        case DependencyType.FS:
            return succ_start - lag
        case DependencyType.SS:
            return succ_start - lag + predecessor_duration
        case DependencyType.FF:
            return succ_finish - lag
        case DependencyType.SF:
            return succ_finish - lag + predecessor_duration


def _free_float(
    task_id: int,
    total_float: int,
    early_start: dict[int, int],
    early_finish: dict[int, int],
    successors: dict[int, list[Dependency]],
    project_length: int,
) -> int:
    """Holgura libre: cuánto puede retrasarse la tarea sin mover a ninguna sucesora."""
    if not successors[task_id]:
        return max(0, min(total_float, project_length - early_finish[task_id]))

    candidates: list[int] = []
    for dependency in successors[task_id]:
        succ = dependency.successor_id
        lag = dependency.lag_days
        match dependency.type:
            case DependencyType.FS:
                candidates.append(early_start[succ] - lag - early_finish[task_id])
            case DependencyType.SS:
                candidates.append(early_start[succ] - lag - early_start[task_id])
            case DependencyType.FF:
                candidates.append(early_finish[succ] - lag - early_finish[task_id])
            case DependencyType.SF:
                candidates.append(early_finish[succ] - lag - early_start[task_id])
    return max(0, min(total_float, *candidates))


def _finish_date(
    start_offset: int,
    finish_offset: int,
    working_days: list[date],
) -> date:
    """Fecha de fin: último día laborable de la tarea, o el día del hito."""
    if finish_offset > start_offset:
        return working_days[finish_offset - 1]
    return working_days[start_offset]
