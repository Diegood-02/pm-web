"""Pruebas del calendario laboral y de su efecto en las fechas del cronograma."""

from datetime import date

import pytest

from app.scheduling import Calendar, Dependency, Task, compute_schedule

MONDAY = date(2026, 1, 5)
SATURDAY = date(2026, 1, 3)
FRIDAY = date(2026, 1, 9)


def test_fin_de_semana_no_es_laborable() -> None:
    calendar = Calendar()

    assert calendar.is_working_day(MONDAY)
    assert not calendar.is_working_day(date(2026, 1, 10))  # sábado
    assert not calendar.is_working_day(date(2026, 1, 11))  # domingo


def test_feriado_no_es_laborable_aunque_sea_entre_semana() -> None:
    calendar = Calendar(holidays=frozenset({date(2026, 1, 6)}))

    assert not calendar.is_working_day(date(2026, 1, 6))


def test_excepcion_laborable_gana_sobre_feriado_y_fin_de_semana() -> None:
    saturday = date(2026, 1, 10)
    calendar = Calendar(
        holidays=frozenset({MONDAY}),
        extra_working_days=frozenset({saturday, MONDAY}),
    )

    assert calendar.is_working_day(saturday)
    assert calendar.is_working_day(MONDAY)


def test_proyecto_que_inicia_en_fin_de_semana_arranca_el_lunes() -> None:
    result = compute_schedule([Task(1, "A", 5)], [], Calendar(), SATURDAY)

    assert result.project_start == MONDAY
    assert result.tasks[1].start_date == MONDAY
    assert result.tasks[1].finish_date == FRIDAY


def test_duracion_salta_fines_de_semana() -> None:
    tasks = [Task(1, "A", 5), Task(2, "B", 3)]
    deps = [Dependency(1, 2)]

    result = compute_schedule(tasks, deps, Calendar(), MONDAY)

    assert result.tasks[2].start_date == date(2026, 1, 12)
    assert result.tasks[2].finish_date == date(2026, 1, 14)
    assert result.project_finish == date(2026, 1, 14)


def test_feriado_desplaza_la_fecha_de_fin() -> None:
    # Lunes 5, miércoles 7 y jueves 8 (el martes 6 es feriado): termina el jueves 8.
    calendar = Calendar(holidays=frozenset({date(2026, 1, 6)}))

    result = compute_schedule([Task(1, "A", 3)], [], calendar, MONDAY)

    assert result.tasks[1].finish_date == date(2026, 1, 8)


def test_hito_toma_la_fecha_del_dia_en_que_ocurre() -> None:
    tasks = [Task(1, "A", 3), Task(2, "Hito", 0, is_milestone=True)]
    deps = [Dependency(1, 2)]
    calendar = Calendar(holidays=frozenset({date(2026, 1, 6)}))

    result = compute_schedule(tasks, deps, calendar, MONDAY)

    # El hito ocurre al inicio del cuarto día laborable: viernes 9.
    assert result.tasks[2].start_date == FRIDAY
    assert result.tasks[2].finish_date == FRIDAY


def test_dia_excepcional_laborable_cuenta_como_dia_de_trabajo() -> None:
    # Viernes 9 (0) y sábado 10 excepcional (1): la tarea de 2 días termina el sábado.
    saturday = date(2026, 1, 10)
    calendar = Calendar(extra_working_days=frozenset({saturday}))

    result = compute_schedule([Task(1, "A", 2)], [], calendar, FRIDAY)

    assert result.tasks[1].finish_date == saturday


def test_calendario_sin_dias_laborables_falla() -> None:
    with pytest.raises(ValueError):
        Calendar(working_weekdays=frozenset())


def test_horas_por_dia_debe_ser_positivo() -> None:
    with pytest.raises(ValueError):
        Calendar(hours_per_day=0)
