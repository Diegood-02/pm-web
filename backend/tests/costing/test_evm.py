"""Pruebas del motor de costos y valor ganado con valores calculados a mano.

Escenario de referencia (horas por día = 8, calendario lunes a viernes):
- Tarea A: 5 días, Ana a 100/h al 100 %, costo fijo 500. Presupuesto = 100*8*5 + 500 = 4 500.
- Tarea B: 2 días, Beto a 50/h al 50 %. Presupuesto = 50*0.5*8*2 = 400.
- Presupuesto total (BAC) = 4 900.
- A empieza el lunes 5 de enero y termina el viernes 9. B empieza el lunes 12.
- Fecha de corte: miércoles 7 de enero. A lleva 3 de 5 días: PV_A = 4 500 * 3/5 = 2 700. B: 0.
- Avance: A al 50 % → EV = 2 250. Costo real de A: 2 400 → AC = 2 400.
- CPI = 2 250 / 2 400 = 0.9375 (sin alerta). SPI = 2 250 / 2 700 = 0.8333 (alerta).
- CV = 2 250 - 2 400 = -150. SV = 2 250 - 2 700 = -450.
"""

from datetime import date
from decimal import Decimal

from app.costing.evm import (
    TaskEvm,
    labor_cost,
    planned_fraction,
    summarize,
    task_budget,
)
from app.scheduling import Calendar

CAL = Calendar()
MON = date(2026, 1, 5)
WED = date(2026, 1, 7)
FRI = date(2026, 1, 9)
MON_12 = date(2026, 1, 12)


def test_costo_de_mano_de_obra_considera_dedicacion_y_horas() -> None:
    assert labor_cost(Decimal("100"), 100, 8, 5) == Decimal("4000.00")
    assert labor_cost(Decimal("50"), 50, 8, 2) == Decimal("400.00")
    assert labor_cost(Decimal("80"), 100, 7.5, 4) == Decimal("2400.00")


def test_presupuesto_de_tarea_suma_asignaciones_y_costo_fijo() -> None:
    assert task_budget([Decimal("4000"), Decimal("250")], Decimal("500")) == Decimal("4750.00")
    assert task_budget([], Decimal("0")) == Decimal("0.00")


def test_fraccion_planeada_sigue_los_dias_laborables() -> None:
    # Miércoles: 3 de 5 días de la tarea A.
    assert planned_fraction(MON, FRI, 5, WED, CAL) == Decimal("3") / Decimal("5")


def test_fraccion_planeada_es_cero_antes_de_empezar_y_uno_al_terminar() -> None:
    assert planned_fraction(MON_12, date(2026, 1, 13), 2, WED, CAL) == Decimal("0")
    assert planned_fraction(MON, FRI, 5, date(2026, 1, 20), CAL) == Decimal("1")


def test_fraccion_planeada_salta_fines_de_semana_y_feriados() -> None:
    calendar = Calendar(holidays=frozenset({date(2026, 1, 6)}))

    # Lunes 5 y miércoles 7 son los dos primeros días laborables de la tarea.
    assert planned_fraction(MON, FRI, 5, WED, calendar) == Decimal("2") / Decimal("5")


def test_hito_vale_todo_al_llegar_a_su_fecha() -> None:
    assert planned_fraction(FRI, FRI, 0, FRI, CAL) == Decimal("1")
    assert planned_fraction(FRI, FRI, 0, WED, CAL) == Decimal("0")


def test_escenario_de_referencia_completo() -> None:
    items = [
        TaskEvm(
            task_id=1,
            budget=Decimal("4500"),
            planned_fraction=Decimal("3") / Decimal("5"),
            percent_complete=50,
            actual_cost=Decimal("2400"),
        ),
        TaskEvm(
            task_id=2,
            budget=Decimal("400"),
            planned_fraction=Decimal("0"),
            percent_complete=0,
            actual_cost=Decimal("0"),
        ),
    ]

    summary = summarize(items)

    assert summary.bac == Decimal("4900.00")
    assert summary.pv == Decimal("2700.00")
    assert summary.ev == Decimal("2250.00")
    assert summary.ac == Decimal("2400.00")
    assert summary.cv == Decimal("-150.00")
    assert summary.sv == Decimal("-450.00")
    assert summary.cpi == 0.9375
    assert summary.spi == 0.8333
    assert summary.cpi_alert is False
    assert summary.spi_alert is True


def test_alerta_cuando_el_costo_se_excede() -> None:
    items = [
        TaskEvm(1, Decimal("4500"), Decimal("3") / Decimal("5"), 50, Decimal("3000")),
    ]

    summary = summarize(items)

    # CPI = 2 250 / 3 000 = 0.75
    assert summary.cpi == 0.75
    assert summary.cpi_alert is True


def test_sin_costo_real_el_cpi_no_se_calcula() -> None:
    summary = summarize([TaskEvm(1, Decimal("100"), Decimal("1"), 100, Decimal("0"))])

    assert summary.cpi is None
    assert summary.cpi_alert is False


def test_sin_valor_planeado_el_spi_no_se_calcula() -> None:
    summary = summarize([TaskEvm(1, Decimal("100"), Decimal("0"), 0, Decimal("0"))])

    assert summary.spi is None
    assert summary.spi_alert is False


def test_proyecto_sin_tareas_da_ceros() -> None:
    summary = summarize([])

    assert summary.bac == Decimal("0.00")
    assert summary.cpi is None and summary.spi is None
