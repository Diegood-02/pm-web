"""Pruebas del algoritmo CPM con valores calculados a mano.

Las pruebas aritméticas usan un calendario de 7 días laborables para que
los desplazamientos coincidan con los días. Los calendarios reales van en
test_calendar.py y en la sección de fechas de este archivo.
"""

from datetime import date

import pytest

from app.scheduling import (
    Calendar,
    CyclicDependencyError,
    Dependency,
    DependencyType,
    SchedulingError,
    Task,
    compute_schedule,
)

ALL_DAYS = Calendar(working_weekdays=frozenset(range(7)))
START = date(2026, 1, 5)  # lunes


def _fs(pred: int, succ: int, lag: int = 0) -> Dependency:
    return Dependency(pred, succ, DependencyType.FS, lag)


def test_cadena_lineal_suma_duraciones() -> None:
    tasks = [Task(1, "A", 3), Task(2, "B", 2), Task(3, "C", 4)]
    deps = [_fs(1, 2), _fs(2, 3)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.duration_days == 9
    assert (result.tasks[1].early_start, result.tasks[1].early_finish) == (0, 3)
    assert (result.tasks[2].early_start, result.tasks[2].early_finish) == (3, 5)
    assert (result.tasks[3].early_start, result.tasks[3].early_finish) == (5, 9)
    assert result.critical_path == (1, 2, 3)
    assert all(result.tasks[i].total_float == 0 for i in (1, 2, 3))


def test_tareas_en_paralelo_holgura_y_ruta_critica() -> None:
    # A(5) y B(3) empiezan juntas; B tiene 2 días de holgura.
    tasks = [Task(1, "A", 5), Task(2, "B", 3)]

    result = compute_schedule(tasks, [], ALL_DAYS, START)

    assert result.duration_days == 5
    assert result.tasks[1].is_critical
    assert not result.tasks[2].is_critical
    assert result.tasks[2].late_start == 2
    assert result.tasks[2].total_float == 2
    assert result.tasks[2].free_float == 2
    assert result.critical_path == (1,)


def test_holgura_en_convergencia_con_cola_paralela() -> None:
    # A(3) y B(2) convergen en C(4). D(2) sale de A y no es crítica.
    tasks = [Task(1, "A", 3), Task(2, "B", 2), Task(3, "C", 4), Task(4, "D", 2)]
    deps = [_fs(1, 3), _fs(2, 3), _fs(1, 4)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.duration_days == 7
    assert result.tasks[2].total_float == 1
    assert result.tasks[2].free_float == 1
    assert result.tasks[4].early_start == 3
    assert result.tasks[4].total_float == 2
    assert result.tasks[4].free_float == 2
    assert result.critical_path == (1, 3)


def test_fs_con_retraso_positivo() -> None:
    tasks = [Task(1, "A", 2), Task(2, "B", 3)]

    result = compute_schedule(tasks, [_fs(1, 2, lag=2)], ALL_DAYS, START)

    assert result.tasks[2].early_start == 4
    assert result.duration_days == 7


def test_fs_con_retraso_negativo_solapa_tareas() -> None:
    # B puede empezar 2 días antes de que A termine.
    tasks = [Task(1, "A", 5), Task(2, "B", 3)]

    result = compute_schedule(tasks, [_fs(1, 2, lag=-2)], ALL_DAYS, START)

    assert result.tasks[2].early_start == 3
    assert result.duration_days == 6


def test_ss_inicio_a_inicio() -> None:
    tasks = [Task(1, "A", 5), Task(2, "B", 3)]
    deps = [Dependency(1, 2, DependencyType.SS, 2)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.tasks[2].early_start == 2
    assert result.tasks[2].early_finish == 5
    assert result.duration_days == 5
    # Ambas terminan en el mismo día del proyecto, así que las dos son críticas.
    assert result.critical_path == (1, 2)


def test_ff_fin_a_fin_calcula_inicio_de_sucesora() -> None:
    # B debe terminar 1 día después de A: EF_B >= EF_A + 1 = 6, así B empieza en 3.
    tasks = [Task(1, "A", 5), Task(2, "B", 3)]
    deps = [Dependency(1, 2, DependencyType.FF, 1)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.tasks[2].early_start == 3
    assert result.tasks[2].early_finish == 6
    assert result.duration_days == 6
    assert result.critical_path == (1, 2)


def test_sf_inicio_a_fin() -> None:
    # B debe terminar al menos 2 días después de que A empiece: EF_B >= 0 + 2 = 2.
    # Como B dura 3 días y arranca en 0, termina en 3, así que no hay retraso.
    tasks = [Task(1, "A", 4), Task(2, "B", 3)]
    deps = [Dependency(1, 2, DependencyType.SF, 2)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.tasks[2].early_start == 0
    assert result.tasks[2].early_finish == 3
    assert result.duration_days == 4


def test_sf_obliga_a_retrasar_la_sucesora() -> None:
    # A empieza en 0, B debe terminar en >= 6 y dura 2 días: empieza en 4.
    tasks = [Task(1, "A", 3), Task(2, "B", 2)]
    deps = [Dependency(1, 2, DependencyType.SF, 6)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.tasks[2].early_start == 4
    assert result.tasks[2].early_finish == 6


def test_hito_no_consume_tiempo() -> None:
    tasks = [
        Task(1, "A", 3),
        Task(2, "Hito", 0, is_milestone=True),
        Task(3, "C", 2),
    ]
    deps = [_fs(1, 2), _fs(2, 3)]

    result = compute_schedule(tasks, deps, ALL_DAYS, START)

    assert result.tasks[2].early_start == 3
    assert result.tasks[2].early_finish == 3
    assert result.tasks[3].early_start == 3
    assert result.duration_days == 5
    assert result.critical_path == (1, 2, 3)


def test_ciclo_debe_fallar_con_error_claro() -> None:
    tasks = [Task(1, "A", 1), Task(2, "B", 1), Task(3, "C", 1), Task(4, "D", 1)]
    deps = [_fs(1, 2), _fs(2, 3), _fs(3, 1), _fs(3, 4)]

    with pytest.raises(CyclicDependencyError) as error:
        compute_schedule(tasks, deps, ALL_DAYS, START)

    assert error.value.task_ids == [1, 2, 3]
    assert "1, 2, 3" in str(error.value)


def test_auto_dependencia_es_ciclo_invalido() -> None:
    with pytest.raises(ValueError):
        Dependency(1, 1)


def test_dependencia_a_tarea_inexistente_falla() -> None:
    with pytest.raises(SchedulingError):
        compute_schedule([Task(1, "A", 1)], [_fs(1, 99)], ALL_DAYS, START)


def test_id_de_tarea_repetido_falla() -> None:
    with pytest.raises(SchedulingError):
        compute_schedule([Task(1, "A", 1), Task(1, "B", 1)], [], ALL_DAYS, START)


def test_duracion_negativa_falla() -> None:
    with pytest.raises(ValueError):
        Task(1, "A", -1)


def test_hito_con_duracion_falla() -> None:
    with pytest.raises(ValueError):
        Task(1, "Hito", 2, is_milestone=True)


def test_sin_tareas_produce_cronograma_vacio() -> None:
    result = compute_schedule([], [], ALL_DAYS, START)

    assert result.tasks == {}
    assert result.duration_days == 0
    assert result.critical_path == ()
