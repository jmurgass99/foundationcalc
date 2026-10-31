"""P0-A req.6: una cimentacion SIN esfuerzos actuantes no puede firmar.

Prueba de integracion, no unitaria: entra por la API real de produccion
(`distribute_loads_rigid_cap`) y comprueba el veredicto que sale de ella, no el de
`resolve_status` en aislamiento. Es la diferencia entre "el contrato es correcto" y
"la ruta de produccion es correcta".

El razonamiento fisico: una accion total identicamente nula sobre un encepado no es
"demanda cero verificada", es que no se aplico ninguna accion -- es decir, que el
analisis no se llego a correr. Una zapata real siempre recibe al menos la carga de
su pilar. Una solicitacion pequeña pero NO nula si es un resultado, y si puede
firmar; eso se comprueba tambien aqui para que el control no impida el trabajo
legitimo.
"""
from __future__ import annotations

from foundationcalc.analysis.pile_group import (
    PileGroup,
    PileInGroup,
    distribute_loads_rigid_cap,
)
from foundationcalc._common.audit_status import CalculationStatus

FAVORABLES = (CalculationStatus.CALCULADO_CUMPLE,)


def _grupo(*, con_capacidades: bool = True) -> PileGroup:
    """Cuatro pilotes en cuadrado, con o sin capacidades declaradas."""
    cap = dict(axial_capacity_kN=1200.0, tension_capacity_kN=400.0,
               lateral_capacity_kN=150.0) if con_capacidades else {}
    return PileGroup(
        piles=[
            PileInGroup(x_m=x, y_m=y, diameter_m=0.6, name=f"P{i + 1}", **cap)
            for i, (x, y) in enumerate(((-1.5, -1.5), (1.5, -1.5), (1.5, 1.5), (-1.5, 1.5)))
        ],
        spacing_m=3.0, arrangement_rows=2, arrangement_cols=2,
    )


def test_una_cimentacion_sin_esfuerzos_actuantes_no_firma() -> None:
    """EL CASO CRITICO. Cero acciones -> nunca CALCULADO_CUMPLE."""
    res = distribute_loads_rigid_cap(_grupo(), V_kN=0.0)

    assert res.status not in FAVORABLES, (
        "una cimentacion sin ninguna accion aplicada firmo un veredicto favorable"
    )
    assert res.status in (CalculationStatus.NO_CALCULADO,
                          CalculationStatus.REQUIERE_REVISION)
    assert res.all_ok is False


def test_una_cimentacion_sin_esfuerzos_ni_capacidades_tampoco_firma() -> None:
    """Ni por el camino de "no hay nada que comprobar, luego cumple"."""
    res = distribute_loads_rigid_cap(_grupo(con_capacidades=False), V_kN=0.0)

    assert res.status not in FAVORABLES
    assert res.all_ok is False


def test_ningun_pilote_individual_firma_sin_esfuerzos() -> None:
    """El veredicto por pilote es tan exigible como el del grupo.

    Si el grupo se blinda pero cada `PileForce` sigue naciendo en CUMPLE, cualquier
    consumidor que lea el detalle en vez del resumen ve aprobados inventados.
    """
    res = distribute_loads_rigid_cap(_grupo(), V_kN=0.0)

    assert res.forces, "el grupo no produjo fuerzas por pilote"
    for f in res.forces:
        assert f.status not in FAVORABLES, f"{f.pile_name} firmo sin esfuerzos"


def test_el_default_del_dataclass_ya_no_es_un_veredicto_favorable() -> None:
    """Construir el resultado sin pensar en el veredicto no debe aprobar nada.

    `PileForce.status` y `PileGroupResult.status` tenian
    `= CalculationStatus.CALCULADO_CUMPLE` como valor por defecto: la misma
    "omision = cumplimiento" que la Proof Obligation prohibe, escrita como default
    de dataclass.
    """
    from foundationcalc.analysis.pile_group import PileForce

    f = PileForce(
        pile_name="P1", x_m=0.0, y_m=0.0, N_kN=100.0, H_x_kN=0.0, H_y_kN=0.0,
        axial_utilization=None, lateral_utilization=None, in_compression=True,
    )
    assert f.status is CalculationStatus.NO_CALCULADO


# --------------------------------------------------------------------------- #
# El control no puede impedir el trabajo legitimo
# --------------------------------------------------------------------------- #
def test_con_esfuerzos_reales_y_capacidades_declaradas_si_firma() -> None:
    """Demanda real holgada + capacidades declaradas -> CUMPLE."""
    res = distribute_loads_rigid_cap(_grupo(), V_kN=1600.0)

    assert res.status is CalculationStatus.CALCULADO_CUMPLE, res.missing_inputs
    assert res.all_ok is True
    assert res.group_axial_utilization is not None
    assert res.group_axial_utilization < 1.0


def test_un_grupo_sobrecargado_con_evidencia_completa_da_falla() -> None:
    """Y cuando de verdad no cumple, dice FALLA -- no NO_CALCULADO."""
    res = distribute_loads_rigid_cap(_grupo(), V_kN=12000.0)

    assert res.status is CalculationStatus.CALCULADO_FALLA, res.missing_inputs
    assert res.all_ok is False
    assert res.group_axial_utilization is not None
    assert res.group_axial_utilization > 1.0


def test_una_capacidad_ausente_con_demanda_presente_no_firma() -> None:
    """La ausencia sigue dominando: demanda real sin capacidad no es CUMPLE."""
    res = distribute_loads_rigid_cap(_grupo(con_capacidades=False), V_kN=1600.0)

    assert res.status not in FAVORABLES
    assert res.missing_inputs, "no se reporto que faltaba la capacidad"
